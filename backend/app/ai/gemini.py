import threading
import time

import httpx
from google import genai
from google.genai import errors, types

from app.ai.base import GenerationError, GenerationRequest, GenerationResponse

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
# Errors that are specific to one model (overloaded, quota, retired), so the next fallback model may still work.
_TRY_NEXT_MODEL = {404, 429, 500, 503, 504}


class GeminiGenerator:
    provider = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int,
        client: genai.Client | None = None,
        fallback_models: tuple[str, ...] = (),
    ) -> None:
        self.model = model
        self.models = list(dict.fromkeys([model, *fallback_models]))
        self.timeout_seconds = timeout_seconds
        self._client = client or genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
        )

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            response_mime_type="application/json",
            response_json_schema=request.response_schema,
            temperature=0.7,
        )
        retryable: GenerationError | None = None
        # One request, fallbacks included, never outlasts timeout x models: the generation lease is sized on that.
        deadline = time.monotonic() + self.timeout_seconds * len(self.models)
        for model in self.models:
            try:
                return self._call_with_deadline(model, request, config, deadline)
            except GenerationError as exc:
                if not isinstance(exc.__cause__, errors.APIError) or exc.__cause__.code not in _TRY_NEXT_MODEL:
                    raise
                if exc.retryable:
                    retryable = exc
                last = exc
        # A transient failure on any model (e.g. 503) wins over a later permanent one (e.g. a retired model's 404).
        raise retryable or last

    def _call_with_deadline(
        self, model: str, request: GenerationRequest, config: types.GenerateContentConfig, deadline: float
    ) -> GenerationResponse:
        """The HTTP timeout only bounds each wait for data, so a slowly trickling reply needs a hard wall-clock limit.

        The call runs in a daemon thread; if it misses the deadline its late reply is discarded, never returned."""
        limit = min(self.timeout_seconds, deadline - time.monotonic())
        if limit <= 0:
            raise GenerationError("Gemini request exceeded its time limit", retryable=True, kind="timeout")
        done = threading.Event()
        outcome: dict = {}

        def run() -> None:
            try:
                outcome["response"] = self._call(model, request, config)
            except BaseException as exc:  # handed to the caller below
                outcome["error"] = exc
            finally:
                done.set()

        threading.Thread(target=run, name=f"gemini-{model}", daemon=True).start()
        if not done.wait(limit):
            raise GenerationError("Gemini request exceeded its time limit", retryable=True, kind="timeout")
        if "error" in outcome:
            raise outcome["error"]
        return outcome["response"]

    def _call(self, model: str, request: GenerationRequest, config: types.GenerateContentConfig) -> GenerationResponse:
        try:
            response = self._client.models.generate_content(model=model, contents=request.prompt, config=config)
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
            model=model,
        )
