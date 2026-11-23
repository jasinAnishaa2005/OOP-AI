import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.ai import ExamGenerator, get_exam_generator
from app.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db import get_db
from app.models import User
from app.schemas import exams as s
from app.services import exams as svc
from app.services.exam_generation import run_generation

router = APIRouter(prefix="/exams", tags=["exams"], dependencies=[Depends(get_current_user)])


def _call(fn, *args):
    try:
        return fn(*args)
    except svc.ExamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/templates", response_model=list[s.TemplateOut])
def templates(db: Session = Depends(get_db)) -> list[s.TemplateOut]:
    return svc.list_templates(db)


@router.post("", response_model=s.ExamOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: get_settings().exam_create_rate_limit)
def create_exam(
    request: Request,
    body: s.ExamCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    generator: ExamGenerator = Depends(get_exam_generator),
    idempotency_key: str | None = Header(default=None, min_length=1, max_length=100),
) -> s.ExamOut:
    exam, created = _call(svc.create_exam, db, user, body, idempotency_key)
    if created:
        background.add_task(run_generation, exam.id, generator)
    return svc.exam_out(svc.get_exam(db, user, exam.id))


@router.get("", response_model=s.ExamList)
def history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> s.ExamList:
    return svc.list_exams(db, user.id, limit, offset)


@router.get("/{exam_id}", response_model=s.ExamOut)
def get_exam(exam_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> s.ExamOut:
    return svc.exam_out(_call(svc.get_exam, db, user, exam_id))


@router.post("/{exam_id}/retry", response_model=s.ExamOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: get_settings().exam_create_rate_limit)
def retry(
    request: Request,
    exam_id: uuid.UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    generator: ExamGenerator = Depends(get_exam_generator),
) -> s.ExamOut:
    exam = _call(svc.retry_exam, db, user, exam_id)
    background.add_task(run_generation, exam.id, generator)
    return svc.exam_out(svc.get_exam(db, user, exam.id))


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(exam_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    _call(svc.delete_exam, db, user, exam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
