import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_NON_NULLABLE = ("name", "sort_order", "is_active", "category_id", "group_id")


def _clean_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    if not value:
        raise ValueError("Name cannot be blank")
    return value


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


# ---------- Read models ----------


class TopicRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str


class TopicOut(TopicRef):
    description: str | None
    sort_order: int
    is_active: bool
    prerequisite_ids: list[uuid.UUID] = []


class GroupOut(TopicRef):
    description: str | None
    sort_order: int
    is_active: bool
    topic_count: int
    topics: list[TopicOut]


class CategorySummary(TopicRef):
    description: str | None
    sort_order: int
    is_active: bool
    group_count: int
    topic_count: int


class CategoryOut(CategorySummary):
    groups: list[GroupOut]


class TopicTree(BaseModel):
    category_count: int
    group_count: int
    topic_count: int
    categories: list[CategoryOut]


class TopicPath(BaseModel):
    """A topic with its location in the hierarchy, for flat lists such as search results."""

    topic: TopicRef
    group: TopicRef
    category: TopicRef


class TopicDetail(TopicOut):
    group: TopicRef
    category: TopicRef
    prerequisites: list[TopicRef]


class SearchResults(BaseModel):
    query: str
    total: int
    results: list[TopicPath]


class SelectionRequest(BaseModel):
    """Any mix of whole categories, whole chapters and individual topics."""

    category_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    group_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    topic_ids: list[uuid.UUID] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def _not_empty(self) -> "SelectionRequest":
        if not (self.category_ids or self.group_ids or self.topic_ids):
            raise ValueError("Select at least one category, chapter or topic")
        return self


class CategorySelectionSummary(TopicRef):
    selected_topic_count: int
    total_topic_count: int


class SelectionSummary(BaseModel):
    topic_count: int
    topic_ids: list[uuid.UUID]
    categories: list[CategorySelectionSummary]
    topics: list[TopicPath]


# ---------- Admin write models ----------


class _NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=120, pattern=SLUG_PATTERN)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool = True

    _name = field_validator("name")(_clean_name)


class _NodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None

    _name = field_validator("name")(_clean_name)

    @model_validator(mode="after")
    def _reject_nulls(self):
        for field in _NON_NULLABLE:
            if field in self.model_fields_set and getattr(self, field, None) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CategoryCreate(_NodeCreate):
    pass


class CategoryUpdate(_NodeUpdate):
    pass


class GroupCreate(_NodeCreate):
    category_id: uuid.UUID


class GroupUpdate(_NodeUpdate):
    category_id: uuid.UUID | None = None


class TopicCreate(_NodeCreate):
    group_id: uuid.UUID
    prerequisite_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class TopicUpdate(_NodeUpdate):
    group_id: uuid.UUID | None = None


class ReorderRequest(BaseModel):
    """Every child of the parent, in the desired order."""

    ids: list[uuid.UUID] = Field(min_length=1, max_length=1000)


class PrerequisitesUpdate(BaseModel):
    prerequisite_ids: list[uuid.UUID] = Field(max_length=50)


class SeedResult(BaseModel):
    categories_created: int
    groups_created: int
    topics_created: int
    prerequisites_created: int
