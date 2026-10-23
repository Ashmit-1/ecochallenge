"""Health, metadata, and configuration parsing."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, Settings, get_settings


def test_health_reports_ok(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"]


def test_meta_exposes_disclaimers_and_provider(client: TestClient):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["verification_provider"] == "mock"
    assert "can make mistakes" in body["verification_disclaimer"]
    assert "estimates" in body["environmental_disclaimer"]


def test_root_redirects_to_docs(client: TestClient):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/docs"


def test_openapi_document_lists_the_api(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/challenges" in schema["paths"]
    assert "/api/v1/challenges/{slug}/submissions" in schema["paths"]
    assert "/api/v1/leaderboard" in schema["paths"]


def test_comma_separated_cors_origins_are_parsed():
    settings = Settings(
        _env_file=None,
        secret_key="x",
        cors_origins="http://one.test, http://two.test",
    )
    assert settings.cors_origins == ["http://one.test", "http://two.test"]


def test_json_cors_origins_are_parsed():
    settings = Settings(
        _env_file=None,
        secret_key="x",
        cors_origins='["http://one.test", "http://two.test"]',
    )
    assert settings.cors_origins == ["http://one.test", "http://two.test"]


def test_relative_sqlite_url_is_resolved_against_the_backend_directory():
    settings = Settings(
        _env_file=None, secret_key="x", database_url="sqlite:///./data/test.db"
    )
    assert settings.sqlalchemy_url == f"sqlite:///{BACKEND_DIR / 'data' / 'test.db'}"


def test_upload_limit_is_converted_to_bytes():
    settings = Settings(_env_file=None, secret_key="x", max_upload_mb=6)
    assert settings.max_upload_bytes == 6 * 1024 * 1024


def test_integer_overflow_returns_422_not_500(client: TestClient, register):
    user = register("Overflow User")
    too_big = 2**63  # one past SQLite's signed 64-bit maximum
    assert client.get(f"/api/v1/submissions/{too_big}", headers=user.headers).status_code == 422
    assert client.get(
        f"/api/v1/submissions/{too_big}/image", headers=user.headers
    ).status_code == 422
    assert client.get(
        f"/api/v1/leaderboard?offset={too_big}", headers=user.headers
    ).status_code == 422
    assert client.get(
        f"/api/v1/submissions?offset={too_big}", headers=user.headers
    ).status_code == 422


def test_redoc_is_disabled(client: TestClient):
    assert client.get("/redoc").status_code == 404


def test_oversized_request_body_is_rejected_before_parsing(client: TestClient, monkeypatch):
    # Leaves the middleware with only its 256 KB multipart allowance.
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "oversized@example.com",
            "password": "x" * (300 * 1024),
            "display_name": "Oversized Body",
        },
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body is too large."
