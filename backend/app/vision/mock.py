"""Deterministic offline provider — used by tests and by `VISION_PROVIDER=mock`."""

from __future__ import annotations

from app.vision.base import VerificationRequest, VerificationResult

REJECT_MARKER = b"MOCK-REJECT"


class MockVisionProvider:
    """Approves by default.

    Tests can force a rejection either by constructing ``MockVisionProvider(approve=False)`` or by
    including the bytes ``MOCK-REJECT`` in the uploaded file, which keeps the override local to a
    single request.
    """

    name = "mock"

    def __init__(self, *, approve: bool = True, reason: str | None = None) -> None:
        self._approve = approve
        self._reason = reason

    def verify(self, request: VerificationRequest) -> VerificationResult:
        if self._approve and REJECT_MARKER not in request.image_bytes:
            return VerificationResult(
                approved=True,
                confidence=0.99,
                reason="Offline mock check: photo accepted without an AI review.",
                model="mock",
            )
        return VerificationResult(
            approved=False,
            confidence=0.05,
            reason=self._reason
            or "Offline mock check: the photo did not clearly match this challenge.",
            model="mock",
        )
