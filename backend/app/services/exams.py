import uuid
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.core.time import as_utc, utcnow
from app.models import Exam, ExamGenerationRequest, ExamQuestion, ExamTemplate, ExamTopic, Topic, TopicGroup, User
from app.schemas import exams as s
from app.schemas.topics import TopicPath, TopicRef, slugify
from app.services import topics as topic_service

STALE_GENERATION = timedelta(minutes=15)


class ExamError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _spec(**fields) -> s.ExamSpec:
    try:
        return s.ExamSpec(**fields)
    except ValidationError as exc:
        raise ExamError("; ".join(e["msg"].removeprefix("Value error, ") for e in exc.errors()), 422) from None


# ---------- Templates ----------


def template_out(t: ExamTemplate) -> s.TemplateOut:
    spec = s.ExamSpec(
        difficulty=t.difficulty,
        difficulty_mix=t.difficulty_mix,
        duration_minutes=t.duration_minutes,
        sections=t.sections,
    )
    return s.TemplateOut(
        id=t.id,
        slug=t.slug,
        name=t.name,
        description=t.description,
        exam_type=spec.exam_type,
        difficulty=spec.difficulty,
        difficulty_mix=spec.difficulty_mix,
        duration_minutes=spec.duration_minutes,
        sections=spec.sections,
        question_count=spec.question_count,
        total_marks=spec.total_marks,
        sort_order=t.sort_order,
        is_active=t.is_active,
    )


def list_templates(db: Session, include_inactive: bool = False) -> list[s.TemplateOut]:
    query = select(ExamTemplate).order_by(ExamTemplate.sort_order, ExamTemplate.name)
    if not include_inactive:
        query = query.where(ExamTemplate.is_active)
    return [template_out(t) for t in db.scalars(query)]


def _commit(db: Session, conflict: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ExamError(conflict, 409) from exc


def create_template(db: Session, data: s.TemplateCreate) -> s.TemplateOut:
    spec = _spec(
        difficulty=data.difficulty,
        difficulty_mix=data.difficulty_mix,
        duration_minutes=data.duration_minutes,
        sections=data.sections,
    )
    slug = data.slug or slugify(data.name)[:80].rstrip("-")
    if not slug:
        raise ExamError("Provide a slug: the name has no letters or digits to build one from", 422)
    order = (db.scalar(select(func.max(ExamTemplate.sort_order))) or 0) + 1
    template = ExamTemplate(
        slug=slug,
        name=data.name,
        description=data.description,
        difficulty=spec.difficulty,
        difficulty_mix=spec.difficulty_mix.model_dump(),
        duration_minutes=spec.duration_minutes,
        sections=[sec.model_dump() for sec in spec.sections],
        sort_order=order,
    )
    db.add(template)
    _commit(db, "A template with this name or slug already exists")
    return template_out(template)


def update_template(db: Session, template_id: uuid.UUID, data: s.TemplateUpdate) -> s.TemplateOut:
    template = db.get(ExamTemplate, template_id)
    if template is None:
        raise ExamError("Template not found", 404)
    changes = data.model_dump(exclude_unset=True)
    spec = _spec(
        difficulty=changes.get("difficulty", template.difficulty),
        difficulty_mix=changes.get("difficulty_mix", template.difficulty_mix),
        duration_minutes=changes.get("duration_minutes", template.duration_minutes),
        sections=changes.get("sections", template.sections),
    )
    for field in ("name", "description", "sort_order", "is_active"):
        if field in changes:
            setattr(template, field, changes[field])
    template.difficulty = spec.difficulty
    template.difficulty_mix = spec.difficulty_mix.model_dump()
    template.duration_minutes = spec.duration_minutes
    template.sections = [sec.model_dump() for sec in spec.sections]
    _commit(db, "A template with this name already exists")
    return template_out(template)


# ---------- Exams ----------


def _check_daily_quota(db: Session, user: User) -> None:
    """Creations and retries both count; the ledger survives exam deletion."""
    limit = get_settings().exam_daily_limit
    # Lock the user row so concurrent requests cannot all pass the check (no-op on SQLite, which serialises writes).
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    since = utcnow() - timedelta(days=1)
    used = db.scalar(
        select(func.count())
        .select_from(ExamGenerationRequest)
        .where(ExamGenerationRequest.user_id == user.id, ExamGenerationRequest.created_at >= since)
    )
    if used >= limit:
        raise ExamError(f"Daily limit of {limit} exam generations reached", 429)


def create_exam(db: Session, user: User, data: s.ExamCreate) -> Exam:
    _check_daily_quota(db, user)

    template = None
    if data.template_id is not None:
        template = db.get(ExamTemplate, data.template_id)
        if template is None or not template.is_active:
            raise ExamError("Template not found", 404)

    def pick(field: str, default):
        value = getattr(data, field)
        if value is not None:
            return value
        return getattr(template, field) if template is not None else default

    spec = _spec(
        difficulty=pick("difficulty", "mixed"),
        difficulty_mix=pick("difficulty_mix", s.DEFAULT_DIFFICULTY_MIX),
        duration_minutes=pick("duration_minutes", None),
        sections=pick("sections", None),
    )

    try:
        selection = topic_service.resolve_selection(db, data.topics)
    except topic_service.TopicError as exc:
        raise ExamError(exc.message, exc.status_code) from exc
    if selection.topic_count > s.MAX_EXAM_TOPICS:
        raise ExamError(f"Select at most {s.MAX_EXAM_TOPICS} topics for one exam", 422)

    exam = Exam(
        user_id=user.id,
        template_id=template.id if template else None,
        title=data.title or (template.name if template else "Custom Exam"),
        exam_type=spec.exam_type,
        difficulty=spec.difficulty,
        difficulty_mix=spec.difficulty_mix.model_dump(),
        duration_minutes=spec.duration_minutes,
        total_marks=spec.total_marks,
        sections=[sec.model_dump() for sec in spec.sections],
        status="pending",
        topic_links=[ExamTopic(topic_id=tid, position=i) for i, tid in enumerate(selection.topic_ids)],
    )
    db.add(exam)
    db.flush()
    db.add(ExamGenerationRequest(user_id=user.id, exam_id=exam.id))
    db.commit()
    return exam


def _load(db: Session, exam_id: uuid.UUID, with_keys: bool = False) -> Exam | None:
    question_opts = selectinload(Exam.questions).selectinload(ExamQuestion.topic)
    options = [
        selectinload(Exam.topic_links)
        .selectinload(ExamTopic.topic)
        .selectinload(Topic.group)
        .selectinload(TopicGroup.category),
        question_opts,
    ]
    if with_keys:
        options += [selectinload(Exam.questions).selectinload(ExamQuestion.key), selectinload(Exam.attempts)]
    return db.get(Exam, exam_id, options=options, populate_existing=True)


def get_exam(db: Session, user: User, exam_id: uuid.UUID) -> Exam:
    exam = _load(db, exam_id)
    if exam is None or exam.user_id != user.id:
        raise ExamError("Exam not found", 404)
    return exam


def get_exam_for_admin(db: Session, exam_id: uuid.UUID) -> Exam:
    exam = _load(db, exam_id, with_keys=True)
    if exam is None:
        raise ExamError("Exam not found", 404)
    return exam


def list_exams(
    db: Session, user_id: uuid.UUID | None, limit: int, offset: int, status: str | None = None
) -> s.ExamList:
    where = []
    if user_id is not None:
        where.append(Exam.user_id == user_id)
    if status is not None:
        where.append(Exam.status == status)
    total = db.scalar(select(func.count()).select_from(Exam).where(*where))
    exams = db.scalars(
        select(Exam)
        .where(*where)
        .options(selectinload(Exam.topic_links), selectinload(Exam.questions))
        .order_by(Exam.created_at.desc(), Exam.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return s.ExamList(total=total, items=[exam_summary(e) for e in exams])


def retry_exam(db: Session, user: User, exam_id: uuid.UUID) -> Exam:
    exam = get_exam(db, user, exam_id)
    stale_before = utcnow() - STALE_GENERATION
    stuck = exam.status in ("pending", "generating") and as_utc(exam.updated_at) < stale_before
    if exam.status != "failed" and not stuck:
        raise ExamError("Only failed exams can be regenerated", 409)
    _check_daily_quota(db, user)
    # Compare-and-set so overlapping retries cannot both reset the exam.
    claimed = db.execute(
        update(Exam)
        .where(
            Exam.id == exam.id,
            or_(
                Exam.status == "failed",
                and_(Exam.status.in_(("pending", "generating")), Exam.updated_at < stale_before),
            ),
        )
        .values(status="pending", failure_reason=None, generation_id=None, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    ).rowcount
    if not claimed:
        db.rollback()
        raise ExamError("This exam is already being regenerated", 409)
    db.execute(delete(ExamQuestion).where(ExamQuestion.exam_id == exam.id))
    db.add(ExamGenerationRequest(user_id=user.id, exam_id=exam.id))
    db.commit()
    return exam


def delete_exam(db: Session, user: User, exam_id: uuid.UUID) -> None:
    exam = get_exam(db, user, exam_id)
    db.delete(exam)
    db.commit()


# ---------- Serialisation (answer keys only in admin output) ----------


def _ref(node) -> TopicRef:
    return TopicRef(id=node.id, slug=node.slug, name=node.name)


def exam_summary(exam: Exam) -> s.ExamSummary:
    return s.ExamSummary(
        id=exam.id,
        title=exam.title,
        status=exam.status,
        failure_reason=exam.failure_reason,
        exam_type=exam.exam_type,
        difficulty=exam.difficulty,
        duration_minutes=exam.duration_minutes,
        total_marks=exam.total_marks,
        question_count=sum(sec["count"] for sec in exam.sections),
        topic_count=len(exam.topic_links),
        template_id=exam.template_id,
        created_at=exam.created_at,
        generated_at=exam.generated_at,
    )


def _question(q: ExamQuestion) -> dict:
    return {
        "id": q.id,
        "position": q.position,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "marks": q.marks,
        "topic": _ref(q.topic),
        "stem": q.stem,
        "content": q.content,
    }


def _exam_fields(exam: Exam) -> dict:
    return {
        **exam_summary(exam).model_dump(),
        "difficulty_mix": exam.difficulty_mix,
        "sections": exam.sections,
        "topics": [
            TopicPath(topic=_ref(link.topic), group=_ref(link.topic.group), category=_ref(link.topic.group.category))
            for link in exam.topic_links
        ],
    }


def exam_out(exam: Exam) -> s.ExamOut:
    questions = [s.QuestionOut(**_question(q)) for q in exam.questions] if exam.status == "ready" else []
    return s.ExamOut(**_exam_fields(exam), questions=questions)


def admin_exam_out(exam: Exam) -> s.AdminExamOut:
    return s.AdminExamOut(
        **_exam_fields(exam),
        user_id=exam.user_id,
        provider=exam.provider,
        model=exam.model,
        prompt_version=exam.prompt_version,
        questions=[
            s.AdminQuestionOut(
                **_question(q), answer=q.key.answer, marking_guide=q.key.marking_guide, explanation=q.key.explanation
            )
            for q in exam.questions
        ],
        attempts=[s.AttemptOut.model_validate(a) for a in exam.attempts],
    )
