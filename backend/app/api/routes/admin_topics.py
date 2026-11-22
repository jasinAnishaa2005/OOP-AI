import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db import get_db
from app.schemas import topics as s
from app.seed.topic_library import seed_topic_library
from app.services import topics as svc

router = APIRouter(prefix="/admin/topics", tags=["admin: topics"], dependencies=[Depends(require_admin)])


def _call(fn, *args):
    try:
        return fn(*args)
    except svc.TopicError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _category(category) -> s.CategorySummary:
    return s.CategorySummary(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        sort_order=category.sort_order,
        is_active=category.is_active,
        group_count=len(category.groups),
        topic_count=sum(len(g.topics) for g in category.groups),
    )


def _group(group) -> s.GroupOut:
    topics = [svc._topic_out(t) for t in group.topics]
    return s.GroupOut(
        id=group.id,
        slug=group.slug,
        name=group.name,
        description=group.description,
        sort_order=group.sort_order,
        is_active=group.is_active,
        topic_count=len(topics),
        topics=topics,
    )


@router.get("/tree", response_model=s.TopicTree)
def full_tree(db: Session = Depends(get_db)) -> s.TopicTree:
    """Every category, chapter and topic, including inactive ones."""
    return svc.get_tree(db, include_inactive=True)


@router.get("/{topic_id}", response_model=s.TopicDetail)
def topic_detail(topic_id: uuid.UUID, db: Session = Depends(get_db)) -> s.TopicDetail:
    return _call(svc.get_topic_detail, db, topic_id, True)


@router.post("/seed", response_model=s.SeedResult)
def seed(db: Session = Depends(get_db)) -> s.SeedResult:
    """Add any missing syllabus entries from the built-in library without touching existing ones."""
    return s.SeedResult(**vars(seed_topic_library(db)))


@router.post("/categories", response_model=s.CategorySummary, status_code=status.HTTP_201_CREATED)
def create_category(body: s.CategoryCreate, db: Session = Depends(get_db)) -> s.CategorySummary:
    return _category(_call(svc.create_category, db, body))


@router.patch("/categories/{category_id}", response_model=s.CategorySummary)
def update_category(category_id: uuid.UUID, body: s.CategoryUpdate, db: Session = Depends(get_db)):
    return _category(_call(svc.update_category, db, category_id, body))


@router.put("/categories/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_categories(body: s.ReorderRequest, db: Session = Depends(get_db)) -> Response:
    _call(svc.reorder_categories, db, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/categories/{category_id}/groups/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_groups(category_id: uuid.UUID, body: s.ReorderRequest, db: Session = Depends(get_db)) -> Response:
    _call(svc.reorder_groups, db, category_id, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/groups", response_model=s.GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: s.GroupCreate, db: Session = Depends(get_db)) -> s.GroupOut:
    return _group(_call(svc.create_group, db, body))


@router.patch("/groups/{group_id}", response_model=s.GroupOut)
def update_group(group_id: uuid.UUID, body: s.GroupUpdate, db: Session = Depends(get_db)) -> s.GroupOut:
    return _group(_call(svc.update_group, db, group_id, body))


@router.put("/groups/{group_id}/topics/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_topics(group_id: uuid.UUID, body: s.ReorderRequest, db: Session = Depends(get_db)) -> Response:
    _call(svc.reorder_topics, db, group_id, body.ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=s.TopicDetail, status_code=status.HTTP_201_CREATED)
def create_topic(body: s.TopicCreate, db: Session = Depends(get_db)) -> s.TopicDetail:
    topic = _call(svc.create_topic, db, body)
    return svc.get_topic_detail(db, topic.id, include_inactive=True)


@router.patch("/{topic_id}", response_model=s.TopicDetail)
def update_topic(topic_id: uuid.UUID, body: s.TopicUpdate, db: Session = Depends(get_db)) -> s.TopicDetail:
    _call(svc.update_topic, db, topic_id, body)
    return svc.get_topic_detail(db, topic_id, include_inactive=True)


@router.put("/{topic_id}/prerequisites", response_model=s.TopicDetail)
def set_prerequisites(topic_id: uuid.UUID, body: s.PrerequisitesUpdate, db: Session = Depends(get_db)) -> s.TopicDetail:
    _call(svc.set_prerequisites, db, topic_id, body.prerequisite_ids)
    return svc.get_topic_detail(db, topic_id, include_inactive=True)
