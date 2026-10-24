"""Tests for OpenAIVisionProvider (Cloudflare Workers AI / OpenAI-compatible). No network calls."""

from __future__ import annotations

import httpx
import pytest

from app.vision.base import (
    VerificationRequest,
    VisionConfigurationError,
    VisionProviderError,
)
from app.vision.openai import OpenAIVisionProvider


def _request(image_bytes: bytes = b"fake-png-bytes") -> VerificationRequest:
    return VerificationRequest(
        image_bytes=image_bytes,
        mime_type="image/png",
        challenge_title="Plant a Tree",
        challenge_description="Plant a sapling in your community.",
        evidence_requirements="A photo showing you or the newly planted tree in soil.",
    )


def test_missing_api_key_raises_configuration_error():
    provider = OpenAIVisionProvider(
        api_key="",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
    )
    with pytest.raises(VisionConfigurationError, match="OPENAI_API_KEY"):
        provider.verify(_request())


def test_missing_base_url_raises_configuration_error():
    provider = OpenAIVisionProvider(
        api_key="secret-token",
        base_url="",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
    )
    with pytest.raises(VisionConfigurationError, match="OPENAI_BASE_URL"):
        provider.verify(_request())


def test_missing_model_raises_configuration_error():
    provider = OpenAIVisionProvider(
        api_key="secret-token",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="",
    )
    with pytest.raises(VisionConfigurationError, match="OPENAI_MODEL"):
        provider.verify(_request())


def test_base_url_strips_chat_completions_suffix():
    provider = OpenAIVisionProvider(
        api_key="secret-token",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1/chat/completions/",
        model="cf-vision",
    )
    assert provider._base_url == "https://api.cloudflare.com/client/v4/accounts/123/ai/v1"


def test_successful_approval_parsed():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.cloudflare.com/client/v4/accounts/123/ai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        content = {
            "choices": [
                {
                    "message": {
                        "content": '{"approved": true, "confidence": 0.95, "reason": "Freshly planted sapling in soil."}'
                    }
                }
            ]
        }
        return httpx.Response(200, json=content)

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
        client=client,
    )

    result = provider.verify(_request())
    assert result.approved is True
    assert result.confidence == 0.95
    assert result.reason == "Freshly planted sapling in soil."
    assert result.model == "@cf/meta/llama-3.2-11b-vision-instruct"


def test_successful_rejection_with_markdown_fences():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        raw_text = """```json
{
  "approved": false,
  "confidence": 0.8,
  "reason": "This is a photo of a computer screen rather than actual planting."
}
```"""
        content = {
            "choices": [
                {
                    "message": {
                        "content": raw_text
                    }
                }
            ]
        }
        return httpx.Response(200, json=content)

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
        client=client,
    )

    result = provider.verify(_request())
    assert result.approved is False
    assert result.confidence == 0.8
    assert "computer screen" in result.reason


def test_unreadable_json_raises_provider_error():
    def mock_transport(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "Not JSON at all"}}]})

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="cf-vision",
        client=client,
    )

    with pytest.raises(VisionProviderError, match="unreadable"):
        provider.verify(_request())


def test_empty_content_raises_provider_error():
    def mock_transport(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="cf-vision",
        client=client,
    )

    with pytest.raises(VisionProviderError, match="empty"):
        provider.verify(_request())


def test_http_error_raises_provider_error():
    def mock_transport(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="cf-vision",
        client=client,
    )

    with pytest.raises(VisionProviderError, match="verification service"):
        provider.verify(_request())


def test_truncates_overlong_reason():
    long_reason = "word " * 300
    def mock_transport(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": f'{{"approved": true, "confidence": 0.9, "reason": "{long_reason}"}}'
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(mock_transport))
    provider = OpenAIVisionProvider(
        api_key="test-key",
        base_url="https://api.cloudflare.com/client/v4/accounts/123/ai/v1",
        model="cf-vision",
        client=client,
    )

    result = provider.verify(_request())
    assert len(result.reason) <= 600
    assert result.reason.endswith("...")
