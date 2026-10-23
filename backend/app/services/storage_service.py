"""Upload validation and local-disk storage.

Photos are private evidence, so they are never served statically. The DB stores a relative path
(``{user_id}/{uuid}.{ext}``) and an authenticated route streams the bytes after an ownership check.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings

# Detected from magic bytes, not from the client-supplied content type.
_MIME_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def detect_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(data: bytes) -> str:
    """Return the detected MIME type or raise a 4xx explaining exactly what is wrong."""
    settings = get_settings()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded file is empty.",
        )
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Photos must be {settings.max_upload_mb} MB or smaller.",
        )
    mime = detect_image_mime(data)
    if mime is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, or WebP photo.",
        )
    return mime


def save_image(data: bytes, mime: str, user_id: int) -> str:
    """Write the file and return its path relative to the uploads root."""
    extension = _MIME_EXTENSIONS[mime]
    relative_path = f"{user_id}/{uuid.uuid4().hex}{extension}"
    destination = get_settings().uploads_path / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return relative_path


def resolve_image_path(relative_path: str) -> Path:
    """Resolve safely inside the uploads root; 404 on traversal or absence."""
    root = get_settings().uploads_path.resolve()
    candidate = (root / relative_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")
    return candidate


def read_image(relative_path: str) -> bytes:
    return resolve_image_path(relative_path).read_bytes()


def delete_image(relative_path: str) -> None:
    """Best-effort cleanup. Never raises: a leftover file is harmless."""
    try:
        (get_settings().uploads_path / relative_path).unlink(missing_ok=True)
    except OSError:
        pass
