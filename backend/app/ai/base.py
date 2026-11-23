import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PlannedSlot:
    """One question the server has decided to ask: the AI only writes its content."""

    slot: int
    question_type: str
    difficulty: str
    marks: int
    topic_id: uuid.UUID
    topic_name: str
    topic_path: str
    topic_description: str | None = None


@dataclass
class GenerationRequest:
    question_type: str
    system_instruction: str
    prompt: str
    response_schema: dict
    slots: list[PlannedSlot] = field(default_factory=list)


@dataclass
class GenerationResponse:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None


class GenerationError(Exception):
    """Provider failure. `retryable` covers timeouts, rate limits and server errors."""

    def __init__(self, message: str, *, retryable: bool, kind: str = "provider_error") -> None:
        super().__init__(message)
        self.retryable = retryable
        self.kind = kind


class ExamGenerator(Protocol):
    provider: str
    model: str

    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
