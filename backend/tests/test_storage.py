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
