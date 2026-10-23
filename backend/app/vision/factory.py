"""Selects the configured verification provider."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.vision.base import VisionProvider
from app.vision.gemini import GeminiVisionProvider
from app.vision.mock import MockVisionProvider


@lru_cache(maxsize=1)
def get_vision_provider() -> VisionProvider:
    """FastAPI dependency. Tests override this to inject a specific mock."""
    settings = get_settings()
    if settings.vision_provider == "mock":
        return MockVisionProvider()
    return GeminiVisionProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        timeout_seconds=settings.vision_timeout_seconds,
    )
