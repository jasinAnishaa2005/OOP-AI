from fastapi import HTTPException, status

from app.ai.base import ExamGenerator, GenerationError, GenerationRequest, GenerationResponse, PlannedSlot
from app.config import get_settings

__all__ = [
    "ExamGenerator",
    "GenerationError",
    "GenerationRequest",
    "GenerationResponse",
    "PlannedSlot",
    "get_exam_generator",
]


def get_exam_generator() -> ExamGenerator:
    """FastAPI dependency returning the configured AI provider."""
    settings = get_settings()
    if settings.ai_provider == "gemini":
        if settings.gemini_api_key is None or not settings.gemini_api_key.get_secret_value():
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI exam generation is not configured")
        from app.ai.gemini import GeminiGenerator

        return GeminiGenerator(
            api_key=settings.gemini_api_key.get_secret_value(),
            model=settings.gemini_model,
            timeout_seconds=settings.ai_timeout_seconds,
        )
    from app.ai.fake import FakeGenerator

    return FakeGenerator()
