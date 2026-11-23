import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.topics import SelectionRequest, TopicPath, TopicRef

QuestionType = Literal["mcq", "theory", "code_analysis", "code_writing"]
Difficulty = Literal["easy", "medium", "hard"]
ExamDifficulty = Literal["easy", "medium", "hard", "mixed"]
ExamStatus = Literal["pending", "generating", "ready", "failed"]

QUESTION_TYPES: tuple[str, ...] = ("mcq", "theory", "code_analysis", "code_writing")
QUESTION_TYPE_LABELS = {
    "mcq": "Multiple Choice",
    "theory": "Theory",
    "code_analysis": "Long Code Analysis",
    "code_writing": "Code Writing",
}
MIN_MINUTES_PER_QUESTION = {"mcq": 1, "theory": 4, "code_analysis": 5, "code_writing": 10}
MAX_QUESTIONS_PER_TYPE = {"mcq": 50, "theory": 10, "code_analysis": 6, "code_writing": 4}
MAX_QUESTIONS = 60
MAX_TOTAL_MARKS = 200
MAX_EXAM_TOPICS = 60


class DifficultyMix(BaseModel):
    """Percentages used when difficulty is "mixed"; must add up to 100."""

    easy: int = Field(ge=0, le=100)
    medium: int = Field(ge=0, le=100)
    hard: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _sums_to_100(self) -> "DifficultyMix":
        if self.easy + self.medium + self.hard != 100:
            raise ValueError("Difficulty percentages must add up to 100")
        return self


DEFAULT_DIFFICULTY_MIX = DifficultyMix(easy=30, medium=50, hard=20)


class Section(BaseModel):
    question_type: QuestionType
    count: int = Field(ge=1, le=50)
    marks_each: int = Field(ge=1, le=50)


class ExamSpec(BaseModel):
    """A fully resolved exam format, checked for consistency."""

    difficulty: ExamDifficulty
    difficulty_mix: DifficultyMix
    duration_minutes: int = Field(ge=5, le=240)
    sections: list[Section] = Field(min_length=1, max_length=len(QUESTION_TYPES))

    @model_validator(mode="after")
    def _consistent(self) -> "ExamSpec":
        types = [sec.question_type for sec in self.sections]
        if len(set(types)) != len(types):
            raise ValueError("Each question type may appear only once")
        for sec in self.sections:
            if sec.count > MAX_QUESTIONS_PER_TYPE[sec.question_type]:
                label = QUESTION_TYPE_LABELS[sec.question_type]
                raise ValueError(f"At most {MAX_QUESTIONS_PER_TYPE[sec.question_type]} {label} questions are allowed")
        if self.question_count > MAX_QUESTIONS:
            raise ValueError(f"An exam can have at most {MAX_QUESTIONS} questions")
        if self.total_marks > MAX_TOTAL_MARKS:
            raise ValueError(f"An exam can be worth at most {MAX_TOTAL_MARKS} marks")
        needed = sum(MIN_MINUTES_PER_QUESTION[sec.question_type] * sec.count for sec in self.sections)
        if self.duration_minutes < needed:
            raise ValueError(f"These questions need at least {needed} minutes")
        return self

    @property
    def question_count(self) -> int:
        return sum(sec.count for sec in self.sections)

    @property
    def total_marks(self) -> int:
        return sum(sec.count * sec.marks_each for sec in self.sections)

    @property
    def exam_type(self) -> str:
        return self.sections[0].question_type if len(self.sections) == 1 else "mixed"


# ---------- Templates ----------


class TemplateOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    exam_type: str
    difficulty: ExamDifficulty
    difficulty_mix: DifficultyMix
    duration_minutes: int
    sections: list[Section]
    question_count: int
    total_marks: int
    sort_order: int
    is_active: bool


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=1000)
    difficulty: ExamDifficulty = "mixed"
    difficulty_mix: DifficultyMix = DEFAULT_DIFFICULTY_MIX
    duration_minutes: int
    sections: list[Section]


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    difficulty: ExamDifficulty | None = None
    difficulty_mix: DifficultyMix | None = None
    duration_minutes: int | None = None
    sections: list[Section] | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _no_null_required_fields(self) -> "TemplateUpdate":
        nulls = [f for f in self.model_fields_set - {"description"} if getattr(self, f) is None]
        if nulls:
            raise ValueError(f"{', '.join(sorted(nulls))} cannot be null")
        return self


# ---------- Exams ----------


class ExamCreate(BaseModel):
    """Create an exam from a preset (optionally overriding parts of it) or from a fully custom format."""

    topics: SelectionRequest
    template_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    difficulty: ExamDifficulty | None = None
    difficulty_mix: DifficultyMix | None = None
    duration_minutes: int | None = None
    sections: list[Section] | None = None

    @model_validator(mode="after")
    def _custom_needs_format(self) -> "ExamCreate":
        if self.template_id is None and (self.sections is None or self.duration_minutes is None):
            raise ValueError("Choose a preset template or provide sections and duration_minutes")
        return self


class QuestionOut(BaseModel):
    id: uuid.UUID
    position: int
    question_type: QuestionType
    difficulty: Difficulty
    marks: int
    topic: TopicRef
    stem: str
    content: dict


class AdminQuestionOut(QuestionOut):
    answer: dict
    marking_guide: dict
    explanation: str | None


class ExamSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: ExamStatus
    failure_reason: str | None
    exam_type: str
    difficulty: ExamDifficulty
    duration_minutes: int
    total_marks: int
    question_count: int
    topic_count: int
    template_id: uuid.UUID | None
    created_at: datetime
    generated_at: datetime | None


class ExamOut(ExamSummary):
    difficulty_mix: DifficultyMix
    sections: list[Section]
    topics: list[TopicPath]
    questions: list[QuestionOut]


class ExamList(BaseModel):
    total: int
    items: list[ExamSummary]


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_type: str
    attempt_number: int
    outcome: str
    error: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime


class AdminExamOut(ExamOut):
    user_id: uuid.UUID
    provider: str | None
    model: str | None
    prompt_version: str | None
    questions: list[AdminQuestionOut]
    attempts: list[AttemptOut]
