import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.schemas import topics as s
from app.services import topics as topic_service

router = APIRouter(prefix="/topics", tags=["topics"], dependencies=[Depends(get_current_user)])


def _raise(exc: topic_service.TopicError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=s.TopicTree)
def topic_tree(db: Session = Depends(get_db)) -> s.TopicTree:
    """The full active syllabus: categories -> chapters -> topics, in display order."""
    return topic_service.get_tree(db)


@router.get("/categories", response_model=list[s.CategorySummary])
def categories(db: Session = Depends(get_db)) -> list[s.CategorySummary]:
    return topic_service.list_categories(db)


@router.get("/search", response_model=s.SearchResults)
def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> s.SearchResults:
    try:
        return topic_service.search_topics(db, q, limit)
    except topic_service.TopicError as exc:
        _raise(exc)


@router.post("/selection", response_model=s.SelectionSummary)
def resolve_selection(body: s.SelectionRequest, db: Session = Depends(get_db)) -> s.SelectionSummary:
    """Expand selected categories, chapters and topics into the final topic list and per-category counts."""
    try:
        return topic_service.resolve_selection(db, body)
    except topic_service.TopicError as exc:
        _raise(exc)


@router.get("/{topic_id}", response_model=s.TopicDetail)
def topic_detail(topic_id: uuid.UUID, db: Session = Depends(get_db)) -> s.TopicDetail:
    try:
        return topic_service.get_topic_detail(db, topic_id)
    except topic_service.TopicError as exc:
        _raise(exc)
