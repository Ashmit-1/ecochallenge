"""Storage helpers: magic bytes, limits, traversal protection, cleanup."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.services import storage_service


def test_detects_supported_image_formats():
    assert storage_service.detect_image_mime(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert storage_service.detect_image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert storage_service.detect_image_mime(b"RIFF\x00\x00\x00\x00WEBPrest") == "image/webp"


def test_rejects_unsupported_and_truncated_signatures():
    assert storage_service.detect_image_mime(b"GIF89a") is None
    assert storage_service.detect_image_mime(b"RIFF") is None
    assert storage_service.detect_image_mime(b"") is None


def test_validate_rejects_empty_data():
    with pytest.raises(HTTPException) as caught:
        storage_service.validate_image(b"")
    assert caught.value.status_code == 422


def test_validate_rejects_oversized_data(monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    with pytest.raises(HTTPException) as caught:
        storage_service.validate_image(b"\x89PNG\r\n\x1a\nx")
    assert caught.value.status_code == 413


def test_save_and_read_round_trip():
    relative = storage_service.save_image(b"\x89PNG\r\n\x1a\npayload", "image/png", 7)
    assert relative.startswith("7/")
    assert relative.endswith(".png")
    assert storage_service.read_image(relative) == b"\x89PNG\r\n\x1a\npayload"


def test_resolve_refuses_to_escape_the_uploads_root(tmp_path):
    root = get_settings().uploads_path
    root.mkdir(parents=True, exist_ok=True)
    (tmp_path / "outside.txt").write_text("secret")

    with pytest.raises(HTTPException) as caught:
        storage_service.resolve_image_path("../outside.txt")
    assert caught.value.status_code == 404


def test_resolve_missing_file_is_404():
    with pytest.raises(HTTPException) as caught:
        storage_service.resolve_image_path("0/missing.png")
    assert caught.value.status_code == 404


def test_delete_is_best_effort_and_never_raises():
    storage_service.delete_image("0/never-existed.png")  # must not raise


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeR2:
    """Just enough of the S3 client for the storage service."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, Bucket, Key, Body, ContentType):  # noqa: N803
        self.objects[Key] = (Body, ContentType)

    def get_object(self, *, Bucket, Key):  # noqa: N803
        if Key not in self.objects:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": _FakeBody(self.objects[Key][0])}

    def delete_object(self, *, Bucket, Key):  # noqa: N803
        self.objects.pop(Key, None)


@pytest.fixture()
def r2(monkeypatch):
    fake = _FakeR2()
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_backend", "r2")
    monkeypatch.setattr(settings, "r2_bucket", "ecochallenge-photos")
    monkeypatch.setattr(storage_service, "_r2_client", lambda: fake)
    return fake


def test_r2_round_trip_saves_type_and_reads_bytes(r2):
    relative = storage_service.save_image(b"\x89PNG\r\n\x1a\npayload", "image/png", 3)
    assert relative.startswith("3/")
    assert r2.objects[relative] == (b"\x89PNG\r\n\x1a\npayload", "image/png")
    assert storage_service.read_image(relative) == b"\x89PNG\r\n\x1a\npayload"


def test_r2_delete_removes_the_object(r2):
    relative = storage_service.save_image(b"data", "image/jpeg", 3)
    storage_service.delete_image(relative)
    assert relative not in r2.objects


def test_r2_missing_photo_is_404(r2):
    with pytest.raises(HTTPException) as caught:
        storage_service.read_image("3/missing.png")
    assert caught.value.status_code == 404


def test_r2_incomplete_configuration_fails_loudly(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_backend", "r2")
    monkeypatch.setattr(settings, "r2_account_id", "")
    monkeypatch.setattr(settings, "r2_endpoint_url", "")
    storage_service._r2_client.cache_clear()
    with pytest.raises(RuntimeError, match="R2_ENDPOINT"):
        storage_service._r2_client()


def test_r2_endpoint_derives_from_the_account_and_can_be_overridden():
    from app.core.config import Settings

    account = Settings(_env_file=None, secret_key="x", r2_account_id="abc123")
    assert account.r2_endpoint == "https://abc123.r2.cloudflarestorage.com"

    custom = Settings(
        _env_file=None,
        secret_key="x",
        r2_endpoint_url="http://127.0.0.1:9000",
        r2_bucket="photos",
        r2_access_key_id="key",
        r2_secret_access_key="secret",
    )
    assert custom.r2_endpoint == "http://127.0.0.1:9000"
    assert custom.r2_configured
