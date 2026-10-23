"""Shared test fixtures.

Environment variables are set **before** importing the app so the cached Settings object never
picks up the developer's real .env (and never talks to the real Gemini API).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

os.environ["SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["VISION_PROVIDER"] = "mock"

from typing import Callable  # noqa: E402

from PIL import Image  # noqa: E402
from PIL.PngImagePlugin import PngInfo  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.api.deps import get_session  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.seed import apply_seed  # noqa: E402
from app.main import app  # noqa: E402
from app.vision.factory import get_vision_provider  # noqa: E402
from app.vision.mock import MockVisionProvider  # noqa: E402



@dataclass(frozen=True)
class RegisteredUser:
    user: dict
    password: str
    headers: dict


@pytest.fixture(autouse=True)
def isolated_uploads(tmp_path, monkeypatch):
    """Never write test photos into backend/uploads."""
    settings = get_settings()
    monkeypatch.setattr(settings, "uploads_dir", tmp_path / "uploads")


@pytest.fixture()
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db_session(engine):
    """Direct session for arranging state (backdating timestamps, deactivating data)."""
    with Session(engine) as session:
        yield session


@pytest.fixture()
def seeded(db_session):
    apply_seed(db_session)
    return db_session


@pytest.fixture()
def client(engine, seeded):
    # Mirror production SessionLocal, including autoflush=False, so tests exercise the same
    # staleness/transaction behaviour the app has in production.
    test_session_factory = sessionmaker(
        bind=engine, class_=Session, expire_on_commit=False, autoflush=False
    )

    def override_get_session():
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_vision_provider] = lambda: MockVisionProvider()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def register(client: TestClient) -> Callable[..., RegisteredUser]:
    def _register(
        display_name: str | None = None,
        *,
        email: str | None = None,
        password: str = "correct-horse-battery",
    ) -> RegisteredUser:
        suffix = uuid4().hex[:8]
        payload = {
            "email": email or f"student-{suffix}@example.com",
            "password": password,
            "display_name": display_name or f"Student {suffix}",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        # Registration also starts a cookie session. Most tests authenticate with the bearer
        # token, so clear the jar to keep them from accidentally acting as that user.
        client.cookies.clear()
        return RegisteredUser(
            user=body["user"],
            password=password,
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )

    return _register


@pytest.fixture()
def submit(client: TestClient) -> Callable[..., object]:
    def _submit(
        user: RegisteredUser,
        slug: str = "bike-to-campus",
        image: bytes | None = None,
        filename: str = "proof.png",
        content_type: str = "image/png",
    ):
        return client.post(
            f"/api/v1/challenges/{slug}/submissions",
            headers=user.headers,
            files={"image": (filename, image if image is not None else png_bytes(), content_type)},
        )

    return _submit


def png_bytes(payload: bytes = b"", marker: bytes = b"") -> bytes:
    """A genuinely decodable PNG, unique per call.

    Upload validation now fully decodes images, so tests cannot use bare magic bytes. Metadata
    text chunks carry the mock-rejection marker and a nonce that makes every file byte-unique.
    """
    image = Image.new("RGB", (320, 320), (26, 108, 63))
    nonce = uuid4().int
    image.putpixel((2, 2), (nonce % 256, (nonce >> 8) % 256, (nonce >> 16) % 256))

    info = PngInfo()
    info.add_text("marker", marker.decode("latin-1", "ignore"))
    info.add_text("payload", payload.decode("latin-1", "ignore"))
    info.add_text("nonce", uuid4().hex)

    buffer = BytesIO()
    image.save(buffer, format="PNG", pnginfo=info)
    return buffer.getvalue()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def png() -> Callable[..., bytes]:
    """Factory for valid-looking PNG bytes, optionally carrying a mock-rejection marker."""
    return png_bytes
