import httpx
from google import genai
from google.genai import errors, types

from app.ai.base import GenerationError, GenerationRequest, GenerationResponse

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class GeminiGenerator:
    provider = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int, client: genai.Client | None = None) -> None:
        self.model = model
        self._client = client or genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=timeout_seconds * 1000)
        )

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            response_mime_type="application/json",
            response_json_schema=request.response_schema,
            temperature=0.7,
        )
        try:
            response = self._client.models.generate_content(model=self.model, contents=request.prompt, config=config)
        except errors.APIError as exc:
            kind = "rate_limited" if exc.code == 429 else "provider_error"
            raise GenerationError(
                f"Gemini API error {exc.code}", retryable=exc.code in _RETRYABLE_STATUS, kind=kind
            ) from exc
        except httpx.TimeoutException as exc:
            raise GenerationError("Gemini request timed out", retryable=True, kind="timeout") from exc
        except httpx.HTTPError as exc:
            raise GenerationError(f"Gemini connection error: {type(exc).__name__}", retryable=True) from exc

        text = response.text
        if not text:
            raise GenerationError("Gemini returned an empty response", retryable=True, kind="invalid_output")
        usage = response.usage_metadata
        return GenerationResponse(
            text=text,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
