import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db import get_db
from app.schemas import exams as s
from app.services import exams as svc

router = APIRouter(prefix="/admin", tags=["admin: exams"], dependencies=[Depends(require_admin)])


def _call(fn, *args):
    try:
        return fn(*args)
    except svc.ExamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/exam-templates", response_model=list[s.TemplateOut])
def templates(db: Session = Depends(get_db)) -> list[s.TemplateOut]:
    return svc.list_templates(db, include_inactive=True)


@router.post("/exam-templates", response_model=s.TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: s.TemplateCreate, db: Session = Depends(get_db)) -> s.TemplateOut:
    return _call(svc.create_template, db, body)


@router.patch("/exam-templates/{template_id}", response_model=s.TemplateOut)
def update_template(template_id: uuid.UUID, body: s.TemplateUpdate, db: Session = Depends(get_db)) -> s.TemplateOut:
    return _call(svc.update_template, db, template_id, body)


@router.get("/exams", response_model=s.ExamList)
def exams(
    status_filter: s.ExamStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> s.ExamList:
    return svc.list_exams(db, None, limit, offset, status_filter)


@router.get("/exams/{exam_id}", response_model=s.AdminExamOut)
def exam(exam_id: uuid.UUID, db: Session = Depends(get_db)) -> s.AdminExamOut:
    return svc.admin_exam_out(_call(svc.get_exam_for_admin, db, exam_id))
