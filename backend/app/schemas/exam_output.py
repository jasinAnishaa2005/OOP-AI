"""Structured output the AI must return for each question type (validated before anything is stored)."""

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RubricItem(_Out):
    criterion: str = Field(min_length=3, max_length=400)
    marks: int = Field(ge=1, le=50)


class _Question(_Out):
    slot: int = Field(ge=1)
    question: str = Field(min_length=10, max_length=4000)


class McqQuestion(_Question):
    options: list[str] = Field(min_length=4, max_length=4)
    correct_option: int = Field(ge=0, le=3, description="0-based index of the single correct option")
    explanation: str = Field(min_length=10, max_length=2000)


class TheoryQuestion(_Question):
    model_answer: str = Field(min_length=20, max_length=6000)
    key_points: list[str] = Field(min_length=1, max_length=10)
    rubric: list[RubricItem] = Field(min_length=1, max_length=8)


class CodeAnalysisQuestion(_Question):
    code: str = Field(min_length=1, max_length=8000, description="Complete Java code, 15-120 lines")
    expected_answer: str = Field(min_length=10, max_length=6000)
    rubric: list[RubricItem] = Field(min_length=1, max_length=8)


class TestCase(_Out):
    __test__ = False

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    expected: str = Field(min_length=1, max_length=1000)


class CodeWritingQuestion(_Question):
    starter_code: str = Field(min_length=1, max_length=6000)
    reference_solution: str = Field(min_length=1, max_length=10000)
    test_cases: list[TestCase] = Field(min_length=2, max_length=10)
    rubric: list[RubricItem] = Field(min_length=1, max_length=8)


class McqBatch(_Out):
    questions: list[McqQuestion]


class TheoryBatch(_Out):
    questions: list[TheoryQuestion]


class CodeAnalysisBatch(_Out):
    questions: list[CodeAnalysisQuestion]


class CodeWritingBatch(_Out):
    questions: list[CodeWritingQuestion]


BATCH_MODELS: dict[str, type[_Out]] = {
    "mcq": McqBatch,
    "theory": TheoryBatch,
    "code_analysis": CodeAnalysisBatch,
    "code_writing": CodeWritingBatch,
}
