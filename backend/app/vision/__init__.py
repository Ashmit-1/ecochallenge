"""Photo-evidence verification behind a swappable provider interface."""

from app.vision.base import (
    VerificationRequest,
    VerificationResult,
    VisionConfigurationError,
    VisionError,
    VisionProvider,
    VisionProviderError,
)
from app.vision.factory import get_vision_provider
from app.vision.gemini import GeminiVisionProvider
from app.vision.mock import MockVisionProvider

__all__ = [
    "GeminiVisionProvider",
    "MockVisionProvider",
    "VerificationRequest",
    "VerificationResult",
    "VisionConfigurationError",
    "VisionError",
    "VisionProvider",
    "VisionProviderError",
    "get_vision_provider",
]
