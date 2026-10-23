"""The verification contract every provider implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class VisionError(Exception):
    """Base class for verification failures. Never means 'rejected' — means 'could not check'."""


class VisionConfigurationError(VisionError):
    """The provider is selected but not usable (missing key, bad config)."""


class VisionProviderError(VisionError):
    """The provider was called and failed (network, quota, malformed response)."""


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    """Everything a provider needs to judge one photo. No ORM objects, no HTTP."""

    image_bytes: bytes
    mime_type: str
    challenge_title: str
    challenge_description: str
    evidence_requirements: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    approved: bool
    confidence: float
    reason: str
    model: str


@runtime_checkable
class VisionProvider(Protocol):
    """A swappable photo-verification backend."""

    name: str

    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Judge the photo. Raise a ``VisionError`` subclass if checking is impossible."""
        ...
