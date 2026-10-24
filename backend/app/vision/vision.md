# vision/

Turns a submitted photo into a verdict: `approved`, `confidence`, `reason`.

| File | Role |
|---|---|
| [base.py](base.py) | `VisionProvider` protocol, `VerificationRequest/Result`, error types |
| [mock.py](mock.py) | Deterministic offline provider — default in tests, available in dev |
| [gemini.py](gemini.py) | Live Google Gemini provider, structured JSON output |
| [openai.py](openai.py) | Live OpenAI-compatible provider (Cloudflare Workers AI, vLLM, etc.) |
| [factory.py](factory.py) | Chooses the provider from `VISION_PROVIDER` |
| [__init__.py](__init__.py) | Public re-exports |

## The rule

A provider returns a verdict **or raises**. It never returns "rejected" to signal a failure:

- `VisionConfigurationError` — selected but unusable (missing `GEMINI_API_KEY`).
- `VisionProviderError` — the call failed (network, quota, unparsable output).

`services/submission_service.py` maps either to `status=error` + HTTP `502`, and awards nothing.
This keeps "the AI said no" separate from "we could not ask the AI", which is the difference
between an honest rejection and a student losing points to an outage.

## Gemini specifics

- Model comes from `GEMINI_MODEL` (default `gemma-4-26b-a4b-it`; `gemini-2.5-flash` also works).
  Both were verified live: a campus bicycle photo approved at 0.95 confidence, a laptop photo
  rejected at 1.0 with a concrete reason.
- Responses use `response_schema=VisionVerdict`, so output is validated JSON rather than prose.
- `temperature=0.1` for consistency; `SystemPrompt` in `gemini.py` defines what counts as evidence.
- Timeout from `VISION_TIMEOUT_SECONDS`, applied via `HttpOptions.timeout` (milliseconds).
- The client is created lazily, so importing the app never requires a key.

## Mock specifics

`MockVisionProvider` approves by default. To force a rejection in a test, either construct it with
`approve=False` or include the byte sequence `MOCK-REJECT` in the uploaded image. The reason text
says it is an offline check, so a mock approval can never be mistaken for a real review.

## Adding a provider

1. Implement `verify(request) -> VerificationResult` (sync; the app runs endpoints in a threadpool).
2. Add it to `factory.py` and to the `Literal` in `core/config.py`.
3. Add a test that exercises approve, reject, and failure paths.
