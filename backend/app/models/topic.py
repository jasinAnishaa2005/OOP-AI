import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

topic_prerequisites = Table(
    "topic_prerequisites",
    Base.metadata,
    Column("topic_id", ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
    Column("prerequisite_id", ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, index=True),
    CheckConstraint("topic_id <> prerequisite_id", name="ck_topic_prerequisites_not_self"),
)


class _Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TopicCategory(_Timestamps, Base):
    """Level 1 of the syllabus, e.g. "Design Patterns"."""

    __tablename__ = "topic_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    groups: Mapped[list["TopicGroup"]] = relationship(
        back_populates="category",
        order_by="(TopicGroup.sort_order, TopicGroup.name)",
        cascade="all, delete-orphan",
    )


class TopicGroup(_Timestamps, Base):
    """Level 2 of the syllabus: a chapter or subcategory, e.g. "Creational"."""

    __tablename__ = "topic_groups"
    __table_args__ = (
        UniqueConstraint("category_id", "slug", name="uq_topic_groups_category_slug"),
        UniqueConstraint("category_id", "name", name="uq_topic_groups_category_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topic_categories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    category: Mapped[TopicCategory] = relationship(back_populates="groups")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="group",
        order_by="(Topic.sort_order, Topic.name)",
        cascade="all, delete-orphan",
    )


class Topic(_Timestamps, Base):
    """Level 3 of the syllabus: an individually selectable concept, e.g. "Singleton"."""

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_topics_group_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topic_groups.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    group: Mapped[TopicGroup] = relationship(back_populates="topics")
    prerequisites: Mapped[list["Topic"]] = relationship(
        secondary=topic_prerequisites,
        primaryjoin=lambda: Topic.id == topic_prerequisites.c.topic_id,
        secondaryjoin=lambda: Topic.id == topic_prerequisites.c.prerequisite_id,
        order_by=lambda: Topic.name,
    )
