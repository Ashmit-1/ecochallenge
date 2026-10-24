"""Upload validation and photo storage.

Photos are private evidence, so they are never served statically. The DB stores a relative path
(``{user_id}/{uuid}.{ext}``) and an authenticated route streams the bytes after an ownership check.

Storage is local disk in development and Cloudflare R2 in production (``STORAGE_BACKEND``);
Cloud Run's disk does not survive a restart. Both backends use the same relative paths, so a
submission row does not record which backend wrote it.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

# Detected from magic bytes, not from the client-supplied content type.
_MIME_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_EXPECTED_PILLOW_FORMAT = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}

# Evidence photos below this are unusable as proof (and cheap to fake).
MIN_IMAGE_DIMENSION = 200

# Refuse absurd dimensions before decoding, so a small file cannot expand into gigabytes of pixels.
MAX_IMAGE_PIXELS = 40_000_000


def detect_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _decode_or_415(data: bytes, expected_mime: str) -> None:
    """Fully decode the file, proving it is a real image and not just a magic-byte prefix."""
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="That image has too many pixels. Upload a normally sized photo.",
                )
            image.load()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="That file could not be read as an image. Upload the original photo.",
        ) from exc

    if image_format != _EXPECTED_PILLOW_FORMAT[expected_mime]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file contents do not match a JPEG, PNG, or WebP image.",
        )
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Photos must be at least {MIN_IMAGE_DIMENSION}×{MIN_IMAGE_DIMENSION} pixels "
                "so the activity is visible."
            ),
        )


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
    _decode_or_415(data, mime)
    return mime


def _use_r2() -> bool:
    return get_settings().storage_backend == "r2"


@lru_cache(maxsize=1)
def _r2_client() -> Any:
    """S3-compatible client for Cloudflare R2.

    Imported lazily so local development and the test suite never pay Boto3's import cost.
    """
    settings = get_settings()
    missing = [
        name
        for name, value in (
            ("R2_ENDPOINT", settings.r2_account_id or settings.r2_endpoint_url),
            ("R2_BUCKET", settings.r2_bucket),
            ("R2_ACCESS_KEY_ID", settings.r2_access_key_id),
            ("R2_SECRET_ACCESS_KEY", settings.r2_secret_access_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"STORAGE_BACKEND=r2 but these settings are empty: {', '.join(missing)}.")

    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def _is_missing_object(exc: Exception) -> bool:
    """Recognise "the photo is not in the bucket" without swallowing real outages."""
    from botocore.exceptions import ClientError

    if not isinstance(exc, ClientError):
        return False
    return str(exc.response.get("Error", {}).get("Code")) in {"NoSuchKey", "404", "NotFound"}


def save_image(data: bytes, mime: str, user_id: int) -> str:
    """Write the photo and return its path relative to the storage root."""
    extension = _MIME_EXTENSIONS[mime]
    relative_path = f"{user_id}/{uuid.uuid4().hex}{extension}"
    settings = get_settings()
    if _use_r2():
        _r2_client().put_object(
            Bucket=settings.r2_bucket,
            Key=relative_path,
            Body=data,
            ContentType=mime,
        )
        return relative_path

    destination = settings.uploads_path / relative_path
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
    settings = get_settings()
    if _use_r2():
        try:
            body = _r2_client().get_object(Bucket=settings.r2_bucket, Key=relative_path)["Body"]
            return body.read()
        except Exception as exc:  # noqa: BLE001 - a storage miss becomes a 404, outages re-raise
            if _is_missing_object(exc):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found."
                ) from exc
            raise
    return resolve_image_path(relative_path).read_bytes()


def delete_image(relative_path: str) -> None:
    """Best-effort cleanup. Never raises: a leftover photo is harmless."""
    try:
        settings = get_settings()
        if _use_r2():
            _r2_client().delete_object(Bucket=settings.r2_bucket, Key=relative_path)
            return
        (settings.uploads_path / relative_path).unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
