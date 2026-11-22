import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.topic import Topic, _Timestamps

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ExamTemplate(_Timestamps, Base):
    """A preset exam format (question mix, marks, duration, difficulty); topics are chosen per exam."""

    __tablename__ = "exam_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(10))
    difficulty_mix: Mapped[dict] = mapped_column(JSONType)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    sections: Mapped[list] = mapped_column(JSONType)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Exam(_Timestamps, Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exam_templates.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(160))
    exam_type: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(10))
    difficulty_mix: Mapped[dict] = mapped_column(JSONType)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    total_marks: Mapped[int] = mapped_column(Integer)
    sections: Mapped[list] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(80))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    template: Mapped[ExamTemplate | None] = relationship()
    topic_links: Mapped[list["ExamTopic"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamTopic.position"
    )
    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.position"
    )
    attempts: Mapped[list["ExamGenerationAttempt"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamGenerationAttempt.created_at"
    )


class ExamTopic(Base):
    """Snapshot of the topics an exam was generated from."""

    __tablename__ = "exam_topics"

    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)

    exam: Mapped[Exam] = relationship(back_populates="topic_links")
    topic: Mapped[Topic] = relationship()


class ExamQuestion(Base):
    """Student-facing part of a question. Answers and marking guides live in ExamQuestionKey."""

    __tablename__ = "exam_questions"
    __table_args__ = (UniqueConstraint("exam_id", "position", name="uq_exam_questions_exam_position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question_type: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(10))
    marks: Mapped[int] = mapped_column(Integer)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="RESTRICT"), index=True)
    stem: Mapped[str] = mapped_column(Text)
    content: Mapped[dict] = mapped_column(JSONType)

    exam: Mapped[Exam] = relationship(back_populates="questions")
    topic: Mapped[Topic] = relationship()
    key: Mapped["ExamQuestionKey"] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False, lazy="raise"
    )


class ExamQuestionKey(Base):
    __tablename__ = "exam_question_keys"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exam_questions.id", ondelete="CASCADE"), primary_key=True
    )
    answer: Mapped[dict] = mapped_column(JSONType)
    marking_guide: Mapped[dict] = mapped_column(JSONType)
    explanation: Mapped[str | None] = mapped_column(Text)

    question: Mapped[ExamQuestion] = relationship(back_populates="key")


class ExamGenerationAttempt(Base):
    """One AI call made while generating an exam (for retries, monitoring and cost tracking)."""

    __tablename__ = "exam_generation_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    question_type: Mapped[str] = mapped_column(String(20))
    attempt_number: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exam: Mapped[Exam] = relationship(back_populates="attempts")
