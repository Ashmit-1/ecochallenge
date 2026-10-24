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
from app.vision.openai import OpenAIVisionProvider

__all__ = [
    "GeminiVisionProvider",
    "MockVisionProvider",
    "OpenAIVisionProvider",
    "VerificationRequest",
    "VerificationResult",
    "VisionConfigurationError",
    "VisionError",
    "VisionProvider",
    "VisionProviderError",
    "get_vision_provider",
]
