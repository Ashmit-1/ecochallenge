"""Vision providers: mock behaviour, Gemini parsing, and failure mapping. No network calls."""

from __future__ import annotations

import pytest

from app.vision.base import (
    VerificationRequest,
    VisionConfigurationError,
    VisionProviderError,
)
from app.vision.gemini import GeminiVisionProvider
from app.vision.mock import MockVisionProvider


def _request(image_bytes: bytes = b"image") -> VerificationRequest:
    return VerificationRequest(
        image_bytes=image_bytes,
        mime_type="image/png",
        challenge_title="Bike to Campus",
        challenge_description="Cycle to campus instead of driving.",
        evidence_requirements="A bicycle at a campus stand.",
    )


def test_mock_approves_by_default():
    result = MockVisionProvider().verify(_request())
    assert result.approved is True
    assert result.model == "mock"
    assert "mock" in result.reason.lower()


def test_mock_can_be_forced_to_reject_by_constructor():
    result = MockVisionProvider(approve=False).verify(_request())
    assert result.approved is False
    assert result.confidence < 0.5


def test_mock_rejects_on_marker_bytes_inside_the_image():
    result = MockVisionProvider().verify(_request(b"\x89PNG\r\n\x1a\nMOCK-REJECT"))
    assert result.approved is False


def test_gemini_without_a_key_raises_configuration_error():
    provider = GeminiVisionProvider(api_key="", model="gemini-2.5-flash")
    with pytest.raises(VisionConfigurationError, match="GEMINI_API_KEY"):
        provider.verify(_request())


class _Response:
    def __init__(self, parsed=None, text: str = "") -> None:
        self.parsed = parsed
        self.text = text


class _Models:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.kwargs: dict = {}

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class _Client:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.models = _Models(response=response, error=error)


def _provider_with(response=None, error: Exception | None = None) -> GeminiVisionProvider:
    provider = GeminiVisionProvider(api_key="fake-key", model="gemini-test")
    provider._client = _Client(response=response, error=error)  # type: ignore[assignment]
    return provider


def test_gemini_parses_structured_output_and_sends_the_image():
    provider = _provider_with(
        _Response(parsed={"approved": True, "confidence": 0.82, "reason": "A bicycle is parked."})
    )

    result = provider.verify(_request())

    assert result.approved is True
    assert result.confidence == pytest.approx(0.82)
    assert result.model == "gemini-test"
    assert result.reason == "A bicycle is parked."

    config = provider._client.models.kwargs["config"]  # type: ignore[union-attr]
    assert config.response_mime_type == "application/json"
    contents = provider._client.models.kwargs["contents"]  # type: ignore[union-attr]
    assert len(contents) == 2


def test_gemini_falls_back_to_json_text():
    provider = _provider_with(
        _Response(
            parsed=None,
            text='{"approved": false, "confidence": 0.2, "reason": "No bicycle visible."}',
        )
    )
    result = provider.verify(_request())
    assert result.approved is False
    assert result.reason == "No bicycle visible."


def test_gemini_unreadable_output_becomes_provider_error():
    provider = _provider_with(_Response(parsed=None, text="I think it is fine!"))
    with pytest.raises(VisionProviderError, match="unreadable"):
        provider.verify(_request())


def test_gemini_empty_output_becomes_provider_error():
    provider = _provider_with(_Response(parsed=None, text=""))
    with pytest.raises(VisionProviderError, match="empty"):
        provider.verify(_request())


def test_gemini_sdk_failure_becomes_provider_error():
    provider = _provider_with(error=RuntimeError("quota exceeded"))
    with pytest.raises(VisionProviderError, match="quota exceeded"):
        provider.verify(_request())


def test_gemini_accepts_a_pydantic_verdict_instance():
    from app.vision.gemini import VisionVerdict

    provider = _provider_with(
        _Response(parsed=VisionVerdict(approved=True, confidence=0.6, reason="Clear enough."))
    )
    result = provider.verify(_request())
    assert result.approved is True
    assert result.confidence == pytest.approx(0.6)


def test_gemini_truncates_an_overlong_reason():
    long_reason = "word " * 300
    provider = _provider_with(
        _Response(parsed={"approved": True, "confidence": 0.7, "reason": long_reason})
    )
    result = provider.verify(_request())
    assert len(result.reason) <= 600
    assert result.reason.endswith("...")
