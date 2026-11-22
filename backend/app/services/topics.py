import uuid
from collections.abc import Iterable

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Topic, TopicCategory, TopicGroup
from app.schemas import topics as s


class TopicError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _not_found(kind: str) -> TopicError:
    return TopicError(f"{kind} not found", 404)


# ---------- Serialisation ----------


def _ref(node) -> s.TopicRef:
    return s.TopicRef(id=node.id, slug=node.slug, name=node.name)


def _topic_out(topic: Topic, visible: set[uuid.UUID] | None = None) -> s.TopicOut:
    prereqs = [p.id for p in topic.prerequisites if visible is None or p.id in visible]
    return s.TopicOut(
        id=topic.id,
        slug=topic.slug,
        name=topic.name,
        description=topic.description,
        sort_order=topic.sort_order,
        is_active=topic.is_active,
        prerequisite_ids=prereqs,
    )


def _path(topic: Topic) -> s.TopicPath:
    return s.TopicPath(topic=_ref(topic), group=_ref(topic.group), category=_ref(topic.group.category))


def _is_available(topic: Topic) -> bool:
    """A topic is offered to students only if it and every ancestor are active."""
    return topic.is_active and topic.group.is_active and topic.group.category.is_active


def _load_categories(db: Session) -> list[TopicCategory]:
    stmt = (
        select(TopicCategory)
        .options(selectinload(TopicCategory.groups).selectinload(TopicGroup.topics).selectinload(Topic.prerequisites))
        .order_by(TopicCategory.sort_order, TopicCategory.name)
    )
    return list(db.scalars(stmt))


def get_tree(db: Session, include_inactive: bool = False) -> s.TopicTree:
    categories = _load_categories(db)
    visible: set[uuid.UUID] | None = None
    if not include_inactive:
        visible = {
            t.id for c in categories if c.is_active for g in c.groups if g.is_active for t in g.topics if t.is_active
        }

    out: list[s.CategoryOut] = []
    for category in categories:
        if not include_inactive and not category.is_active:
            continue
        groups: list[s.GroupOut] = []
        for group in category.groups:
            if not include_inactive and not group.is_active:
                continue
            topics = [_topic_out(t, visible) for t in group.topics if include_inactive or t.is_active]
            if not include_inactive and not topics:
                continue
            groups.append(
                s.GroupOut(
                    id=group.id,
                    slug=group.slug,
                    name=group.name,
                    description=group.description,
                    sort_order=group.sort_order,
                    is_active=group.is_active,
                    topic_count=len(topics),
                    topics=topics,
                )
            )
        if not include_inactive and not groups:
            continue
        out.append(
            s.CategoryOut(
                id=category.id,
                slug=category.slug,
                name=category.name,
                description=category.description,
                sort_order=category.sort_order,
                is_active=category.is_active,
                group_count=len(groups),
                topic_count=sum(g.topic_count for g in groups),
                groups=groups,
            )
        )
    return s.TopicTree(
        category_count=len(out),
        group_count=sum(c.group_count for c in out),
        topic_count=sum(c.topic_count for c in out),
        categories=out,
    )


def list_categories(db: Session) -> list[s.CategorySummary]:
    return [s.CategorySummary(**c.model_dump(exclude={"groups"})) for c in get_tree(db).categories]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_topics(db: Session, query: str, limit: int) -> s.SearchResults:
    query = " ".join(query.split())
    if not query:
        raise TopicError("Search query cannot be blank", 422)
    pattern = f"%{_escape_like(query.lower())}%"
    stmt = (
        select(Topic)
        .join(Topic.group)
        .join(TopicGroup.category)
        .options(selectinload(Topic.group).selectinload(TopicGroup.category))
        .where(
            Topic.is_active,
            TopicGroup.is_active,
            TopicCategory.is_active,
            or_(
                func.lower(Topic.name).like(pattern, escape="\\"),
                func.lower(Topic.description).like(pattern, escape="\\"),
                func.lower(TopicGroup.name).like(pattern, escape="\\"),
                func.lower(TopicCategory.name).like(pattern, escape="\\"),
            ),
        )
        .order_by(
            TopicCategory.sort_order,
            TopicCategory.name,
            TopicGroup.sort_order,
            TopicGroup.name,
            Topic.sort_order,
            Topic.name,
        )
    )
    matches = list(db.scalars(stmt))
    q = query.lower()

    def rank(t: Topic) -> int:
        name = t.name.lower()
        if name == q:
            return 0
        if name.startswith(q):
            return 1
        if q in name:
            return 2
        return 3

    matches.sort(key=rank)  # stable: keeps syllabus order within each rank
    return s.SearchResults(query=query, total=len(matches), results=[_path(t) for t in matches[:limit]])


def get_topic_detail(db: Session, topic_id: uuid.UUID, include_inactive: bool = False) -> s.TopicDetail:
    topic = db.get(Topic, topic_id)
    if topic is None or (not include_inactive and not _is_available(topic)):
        raise _not_found("Topic")
    prereqs = [p for p in topic.prerequisites if include_inactive or _is_available(p)]
    return s.TopicDetail(
        **_topic_out(topic).model_dump(exclude={"prerequisite_ids"}),
        prerequisite_ids=[p.id for p in prereqs],
        prerequisites=[_ref(p) for p in prereqs],
        group=_ref(topic.group),
        category=_ref(topic.group.category),
    )


def resolve_selection(db: Session, request: s.SelectionRequest) -> s.SelectionSummary:
    """Expand selected categories/chapters/topics into a de-duplicated, syllabus-ordered topic list."""
    tree = get_tree(db)
    categories = {c.id: c for c in tree.categories}
    groups = {g.id: (c, g) for c in tree.categories for g in c.groups}
    topics = {t.id: (c, g, t) for c in tree.categories for g in c.groups for t in g.topics}

    missing = (
        [str(i) for i in request.category_ids if i not in categories]
        + [str(i) for i in request.group_ids if i not in groups]
        + [str(i) for i in request.topic_ids if i not in topics]
    )
    if missing:
        raise TopicError(f"Unknown or inactive selection: {', '.join(missing)}", 422)

    selected: set[uuid.UUID] = set(request.topic_ids)
    for cid in request.category_ids:
        selected.update(t.id for g in categories[cid].groups for t in g.topics)
    for gid in request.group_ids:
        selected.update(t.id for t in groups[gid][1].topics)

    ordered = [tid for tid in topics if tid in selected]
    summaries = [
        s.CategorySelectionSummary(
            id=c.id,
            slug=c.slug,
            name=c.name,
            selected_topic_count=sum(1 for g in c.groups for t in g.topics if t.id in selected),
            total_topic_count=c.topic_count,
        )
        for c in tree.categories
    ]
    return s.SelectionSummary(
        topic_count=len(ordered),
        topic_ids=ordered,
        categories=[c for c in summaries if c.selected_topic_count],
        topics=[
            s.TopicPath(topic=_ref(topics[tid][2]), group=_ref(topics[tid][1]), category=_ref(topics[tid][0]))
            for tid in ordered
        ],
    )


# ---------- Admin mutations ----------


def _commit(db: Session, conflict: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TopicError(conflict, 409) from exc


def _next_order(db: Session, column, *where) -> int:
    current = db.scalar(select(func.max(column)).where(*where))
    return 0 if current is None else current + 1


def _get(db: Session, model, node_id: uuid.UUID, kind: str):
    node = db.get(model, node_id)
    if node is None:
        raise _not_found(kind)
    return node


def _apply(node, data: dict) -> None:
    for key, value in data.items():
        setattr(node, key, value)


def _slug(data: s._NodeCreate) -> str:
    slug = data.slug or s.slugify(data.name)
    if not slug:
        raise TopicError("Provide a slug: the name has no letters or digits to build one from", 422)
    return slug


def create_category(db: Session, data: s.CategoryCreate) -> TopicCategory:
    category = TopicCategory(
        name=data.name,
        slug=_slug(data),
        description=data.description,
        is_active=data.is_active,
        sort_order=data.sort_order if data.sort_order is not None else _next_order(db, TopicCategory.sort_order),
    )
    db.add(category)
    _commit(db, "A category with this name or slug already exists")
    return category


def update_category(db: Session, category_id: uuid.UUID, data: s.CategoryUpdate) -> TopicCategory:
    category = _get(db, TopicCategory, category_id, "Category")
    _apply(category, data.model_dump(exclude_unset=True))
    _commit(db, "A category with this name already exists")
    return category


def create_group(db: Session, data: s.GroupCreate) -> TopicGroup:
    _get(db, TopicCategory, data.category_id, "Category")
    group = TopicGroup(
        category_id=data.category_id,
        name=data.name,
        slug=_slug(data),
        description=data.description,
        is_active=data.is_active,
        sort_order=data.sort_order
        if data.sort_order is not None
        else _next_order(db, TopicGroup.sort_order, TopicGroup.category_id == data.category_id),
    )
    db.add(group)
    _commit(db, "A chapter with this name or slug already exists in this category")
    return group


def update_group(db: Session, group_id: uuid.UUID, data: s.GroupUpdate) -> TopicGroup:
    group = _get(db, TopicGroup, group_id, "Chapter")
    changes = data.model_dump(exclude_unset=True)
    new_category = changes.get("category_id")
    if new_category is not None and new_category != group.category_id:
        _get(db, TopicCategory, new_category, "Category")
        if "sort_order" not in changes:
            changes["sort_order"] = _next_order(db, TopicGroup.sort_order, TopicGroup.category_id == new_category)
    _apply(group, changes)
    _commit(db, "A chapter with this name or slug already exists in this category")
    return group


def create_topic(db: Session, data: s.TopicCreate) -> Topic:
    _get(db, TopicGroup, data.group_id, "Chapter")
    topic = Topic(
        group_id=data.group_id,
        name=data.name,
        slug=_slug(data),
        description=data.description,
        is_active=data.is_active,
        sort_order=data.sort_order
        if data.sort_order is not None
        else _next_order(db, Topic.sort_order, Topic.group_id == data.group_id),
    )
    db.add(topic)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise TopicError("A topic with this slug, or this name in this chapter, already exists", 409) from exc
    if data.prerequisite_ids:
        _set_prerequisites(db, topic, data.prerequisite_ids)
    _commit(db, "A topic with this slug, or this name in this chapter, already exists")
    return topic


def update_topic(db: Session, topic_id: uuid.UUID, data: s.TopicUpdate) -> Topic:
    topic = _get(db, Topic, topic_id, "Topic")
    changes = data.model_dump(exclude_unset=True)
    new_group = changes.get("group_id")
    if new_group is not None and new_group != topic.group_id:
        _get(db, TopicGroup, new_group, "Chapter")
        if "sort_order" not in changes:
            changes["sort_order"] = _next_order(db, Topic.sort_order, Topic.group_id == new_group)
    _apply(topic, changes)
    _commit(db, "A topic with this name already exists in this chapter")
    db.refresh(topic)
    return topic


def _reorder(db: Session, children: Iterable, ids: list[uuid.UUID]) -> None:
    by_id = {c.id: c for c in children}
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise TopicError("ids must list every item exactly once", 422)
    for index, node_id in enumerate(ids):
        by_id[node_id].sort_order = index
    db.commit()


def reorder_categories(db: Session, ids: list[uuid.UUID]) -> None:
    _reorder(db, db.scalars(select(TopicCategory)), ids)


def reorder_groups(db: Session, category_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
    _reorder(db, _get(db, TopicCategory, category_id, "Category").groups, ids)


def reorder_topics(db: Session, group_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
    _reorder(db, _get(db, TopicGroup, group_id, "Chapter").topics, ids)


_PREREQUISITE_LOCK = 0x0_0A1_70A1C  # arbitrary app-wide advisory lock key


def _set_prerequisites(db: Session, topic: Topic, prerequisite_ids: list[uuid.UUID]) -> None:
    if db.get_bind().dialect.name == "postgresql":
        # Serialise prerequisite edits so two concurrent requests cannot each pass the cycle check.
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _PREREQUISITE_LOCK})
        db.expire(topic, ["prerequisites"])
    ids = list(dict.fromkeys(prerequisite_ids))
    if topic.id in ids:
        raise TopicError("A topic cannot be its own prerequisite", 422)
    prereqs = list(db.scalars(select(Topic).where(Topic.id.in_(ids)))) if ids else []
    if len(prereqs) != len(ids):
        raise TopicError("One or more prerequisite topics do not exist", 422)

    # Reject cycles: the topic must not be reachable from any of its new prerequisites.
    stack, seen = list(prereqs), set()
    while stack:
        node = stack.pop()
        if node.id == topic.id:
            raise TopicError("These prerequisites would create a circular dependency", 422)
        if node.id in seen:
            continue
        seen.add(node.id)
        stack.extend(node.prerequisites)
    topic.prerequisites = prereqs


def set_prerequisites(db: Session, topic_id: uuid.UUID, prerequisite_ids: list[uuid.UUID]) -> Topic:
    topic = _get(db, Topic, topic_id, "Topic")
    _set_prerequisites(db, topic, prerequisite_ids)
    _commit(db, "Could not update prerequisites")
    return topic
