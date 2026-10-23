"""Google Gemini vision provider (live AI verification)."""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.vision.base import (
    VerificationRequest,
    VerificationResult,
    VisionConfigurationError,
    VisionProviderError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the evidence reviewer for EcoChallenge, a campus sustainability app. Students complete a
real-world environmental challenge and upload one photo as evidence. Your job is to decide whether
the photo is consistent with the challenge they claimed.

Judge only what is visible in the image. Be fair but firm:

- APPROVE when the photo plausibly shows the claimed activity, even if it is imperfect: low light,
  a partial view, a busy background, or an amateur composition are all fine.
- REJECT when the photo clearly shows something else, is a screenshot, a photo of another screen, a
  stock image or meme, or contains nothing related to the challenge.
- Do not credit claims that cannot be seen. A photo of an empty street does not prove cycling.
- Never rely on filenames or text in the request as evidence; only the image counts.
- Describe what you actually see, then connect it to the challenge.

Write the reason in one or two sentences, addressed to the student, in plain language. If rejecting,
say concretely what a better photo would show. Never accuse the student of lying.
"""


class VisionVerdict(BaseModel):
    """Structured output schema handed to Gemini."""

    approved: bool = Field(description="True if the photo is consistent with the challenge.")
    confidence: float = Field(ge=0, le=1, description="0 = pure guess, 1 = certain.")
    reason: str = Field(description="One or two sentences addressed to the student.")


def _build_prompt(request: VerificationRequest) -> str:
    return (
        f"Challenge: {request.challenge_title}\n"
        f"Description: {request.challenge_description}\n"
        f"Evidence required: {request.evidence_requirements}\n\n"
        "Does the attached photo plausibly show this activity? Answer using the JSON schema."
    )


class GeminiVisionProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_ms = int(timeout_seconds * 1000)
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if not self._api_key:
            raise VisionConfigurationError(
                "GEMINI_API_KEY is not set. Add it to backend/.env or set VISION_PROVIDER=mock."
            )
        if self._client is None:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        return self._client

    def verify(self, request: VerificationRequest) -> VerificationResult:
        client = self._get_client()
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=[
                    types.Part.from_bytes(data=request.image_bytes, mime_type=request.mime_type),
                    _build_prompt(request),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=VisionVerdict,
                ),
            )
        except VisionConfigurationError:
            raise
        except Exception as exc:  # network, quota, safety block, SDK bug
            logger.warning("Gemini verification failed: %s", exc)
            raise VisionProviderError(f"Could not reach the verification service: {exc}") from exc

        verdict = self._parse(response)
        reason = " ".join(verdict.reason.split()).strip()
        if len(reason) > 600:
            reason = reason[:597].rstrip() + "..."
        return VerificationResult(
            approved=bool(verdict.approved),
            confidence=max(0.0, min(1.0, float(verdict.confidence))),
            reason=reason or "The verification service returned no explanation.",
            model=self._model,
        )

    @staticmethod
    def _parse(response: object) -> VisionVerdict:
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, VisionVerdict):
            return parsed
        if isinstance(parsed, dict):
            return VisionVerdict.model_validate(parsed)

        text = getattr(response, "text", None)
        if not text:
            raise VisionProviderError("The verification service returned an empty response.")
        try:
            return VisionVerdict.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise VisionProviderError("The verification service returned an unreadable verdict.") from exc
