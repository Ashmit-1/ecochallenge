"""OpenAI-compatible vision provider (works with Cloudflare Workers AI, vLLM, Groq, OpenAI)."""

from __future__ import annotations

import base64
import json
import logging
import re

import httpx
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

You MUST respond strictly with a valid JSON object matching this schema:
{
  "approved": boolean,
  "confidence": number between 0.0 and 1.0,
  "reason": "One or two sentences addressed to the student explaining the verdict."
}
"""


class VisionVerdict(BaseModel):
    """Structured output schema expected from the model."""

    approved: bool = Field(description="True if the photo is consistent with the challenge.")
    confidence: float = Field(ge=0, le=1, description="0 = pure guess, 1 = certain.")
    reason: str = Field(description="One or two sentences addressed to the student.")


def _build_prompt(request: VerificationRequest) -> str:
    return (
        f"Challenge: {request.challenge_title}\n"
        f"Description: {request.challenge_description}\n"
        f"Evidence required: {request.evidence_requirements}\n\n"
        "Does the attached photo plausibly show this activity? Return only the JSON object."
    )


class OpenAIVisionProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        url = base_url.strip().rstrip("/")
        if url.endswith("/chat/completions"):
            url = url[: -len("/chat/completions")].rstrip("/")
        self._base_url = url
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds
        self._client = client

    def verify(self, request: VerificationRequest) -> VerificationResult:
        if not self._api_key:
            raise VisionConfigurationError(
                "OPENAI_API_KEY is not set. Add it to environment variables or secret manager."
            )
        if not self._base_url:
            raise VisionConfigurationError("OPENAI_BASE_URL is not set.")
        if not self._model:
            raise VisionConfigurationError("OPENAI_MODEL is not set.")

        b64_image = base64.b64encode(request.image_bytes).decode("utf-8")
        data_url = f"data:{request.mime_type};base64,{b64_image}"

        endpoint = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _build_prompt(request)},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            if self._client is not None:
                response = self._client.post(endpoint, json=payload, headers=headers)
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
        except VisionConfigurationError:
            raise
        except Exception as exc:
            logger.warning("OpenAI vision provider failed: %s", exc)
            raise VisionProviderError(f"Could not reach the verification service: {exc}") from exc

        verdict = self._parse_content(raw_content)
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
    def _parse_content(content: str | dict) -> VisionVerdict:
        if isinstance(content, dict):
            return VisionVerdict.model_validate(content)

        text = (content or "").strip()
        if not text:
            raise VisionProviderError("The verification service returned an empty response.")

        # Strip markdown fences if returned: ```json ... ``` or ``` ... ```
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()

        # Isolate JSON object bounds if commentary surrounds it
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]

        try:
            parsed = json.loads(text)
            return VisionVerdict.model_validate(parsed)
        except Exception as exc:
            raise VisionProviderError(
                f"The verification service returned an unreadable verdict: {exc}"
            ) from exc
