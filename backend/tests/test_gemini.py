from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from app.ai.base import GenerationError, GenerationRequest
from app.ai.gemini import GeminiGenerator

REQUEST = GenerationRequest(
    question_type="mcq", system_instruction="sys", prompt="p", response_schema={"type": "object"}
)


class FakeModels:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def gen(outcome) -> tuple[GeminiGenerator, FakeModels]:
    models = FakeModels(outcome)
    return GeminiGenerator("unused", "gemini-test", 30, client=SimpleNamespace(models=models)), models


def test_structured_request_and_usage():
    usage = SimpleNamespace(prompt_token_count=11, candidates_token_count=22)
    g, models = gen(SimpleNamespace(text='{"questions": []}', usage_metadata=usage))
    res = g.generate(REQUEST)
    assert (res.text, res.input_tokens, res.output_tokens) == ('{"questions": []}', 11, 22)
    call = models.calls[0]
    assert call["model"] == "gemini-test" and call["contents"] == "p"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_json_schema == {"type": "object"}
    assert call["config"].system_instruction == "sys"


@pytest.mark.parametrize(
    ("exc", "retryable", "kind"),
    [
        (errors.APIError(429, {"error": {"message": "quota"}}), True, "rate_limited"),
        (errors.APIError(503, {"error": {"message": "busy"}}), True, "provider_error"),
        (errors.APIError(400, {"error": {"message": "bad"}}), False, "provider_error"),
        (httpx.ReadTimeout("slow"), True, "timeout"),
        (httpx.ConnectError("down"), True, "provider_error"),
    ],
)
def test_errors_mapped(exc, retryable, kind):
    g, _ = gen(exc)
    with pytest.raises(GenerationError) as info:
        g.generate(REQUEST)
    assert (info.value.retryable, info.value.kind) == (retryable, kind)


def test_empty_response_is_retryable():
    g, _ = gen(SimpleNamespace(text=None, usage_metadata=None))
    with pytest.raises(GenerationError) as info:
        g.generate(REQUEST)
    assert info.value.retryable and info.value.kind == "invalid_output"


def test_production_rejects_fake_provider(monkeypatch):
    from app.config import Settings

    with pytest.raises(ValueError, match="AI_PROVIDER"):
        Settings(environment="production", ai_provider="fake", jwt_secret_key="x" * 40)


class ByModel:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs["model"])
        outcome = self.outcomes[kwargs["model"]]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_falls_back_when_primary_model_is_overloaded():
    ok = SimpleNamespace(text='{"questions": []}', usage_metadata=None)
    models = ByModel({"a": errors.APIError(503, {"error": {"message": "busy"}}), "b": ok})
    g = GeminiGenerator("unused", "a", 30, client=SimpleNamespace(models=models), fallback_models=("b",))
    res = g.generate(REQUEST)
    assert models.calls == ["a", "b"] and res.model == "b"


def test_no_fallback_on_request_errors():
    models = ByModel({"a": errors.APIError(400, {"error": {"message": "bad"}}), "b": None})
    g = GeminiGenerator("unused", "a", 30, client=SimpleNamespace(models=models), fallback_models=("b",))
    with pytest.raises(GenerationError):
        g.generate(REQUEST)
    assert models.calls == ["a"]


def test_last_fallback_error_is_raised():
    busy = errors.APIError(503, {"error": {"message": "busy"}})
    models = ByModel({"a": busy, "b": busy})
    g = GeminiGenerator("unused", "a", 30, client=SimpleNamespace(models=models), fallback_models=("b", "a"))
    with pytest.raises(GenerationError) as info:
        g.generate(REQUEST)
    assert models.calls == ["a", "b"] and info.value.retryable


def test_transient_error_wins_over_later_missing_model():
    models = ByModel(
        {
            "a": errors.APIError(503, {"error": {"message": "busy"}}),
            "b": errors.APIError(404, {"error": {"message": "gone"}}),
        }
    )
    g = GeminiGenerator("unused", "a", 30, client=SimpleNamespace(models=models), fallback_models=("b",))
    with pytest.raises(GenerationError) as info:
        g.generate(REQUEST)
    assert models.calls == ["a", "b"] and info.value.retryable
