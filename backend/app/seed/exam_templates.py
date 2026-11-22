from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExamTemplate
from app.schemas.exams import DEFAULT_DIFFICULTY_MIX, ExamSpec


def _sec(question_type: str, count: int, marks_each: int) -> dict:
    return {"question_type": question_type, "count": count, "marks_each": marks_each}


EXAM_TEMPLATES: list[dict] = [
    {
        "slug": "quick-quiz",
        "name": "Quick Quiz",
        "description": "Ten quick multiple-choice questions.",
        "duration_minutes": 15,
        "sections": [_sec("mcq", 10, 1)],
    },
    {
        "slug": "theory-test",
        "name": "Theory Test",
        "description": "Written explanations of OOP concepts.",
        "duration_minutes": 40,
        "sections": [_sec("theory", 5, 4)],
    },
    {
        "slug": "code-analysis-drill",
        "name": "Code Analysis Drill",
        "description": "Read longer Java programs and analyse their design and behaviour.",
        "duration_minutes": 30,
        "sections": [_sec("code_analysis", 3, 5)],
    },
    {
        "slug": "code-writing-lab",
        "name": "Code Writing Lab",
        "description": "Write Java code for OOP problems.",
        "duration_minutes": 45,
        "sections": [_sec("code_writing", 2, 10)],
    },
    {
        "slug": "midterm",
        "name": "Midterm Exam",
        "description": "A balanced mix of every question type.",
        "duration_minutes": 90,
        "sections": [
            _sec("mcq", 20, 1),
            _sec("theory", 3, 5),
            _sec("code_analysis", 2, 5),
            _sec("code_writing", 1, 10),
        ],
    },
    {
        "slug": "final",
        "name": "Final Exam",
        "description": "A full-length final examination.",
        "duration_minutes": 150,
        "sections": [
            _sec("mcq", 30, 1),
            _sec("theory", 4, 5),
            _sec("code_analysis", 2, 10),
            _sec("code_writing", 2, 15),
        ],
    },
]


def seed_exam_templates(db: Session, templates: list[dict] = EXAM_TEMPLATES) -> int:
    """Insert missing preset templates (matched by slug); existing ones and admin edits are left untouched."""
    existing = set(db.scalars(select(ExamTemplate.slug)))
    created = 0
    for order, data in enumerate(templates):
        if data["slug"] in existing:
            continue
        spec = ExamSpec(
            difficulty="mixed",
            difficulty_mix=DEFAULT_DIFFICULTY_MIX,
            duration_minutes=data["duration_minutes"],
            sections=data["sections"],
        )
        db.add(
            ExamTemplate(
                slug=data["slug"],
                name=data["name"],
                description=data["description"],
                difficulty=spec.difficulty,
                difficulty_mix=spec.difficulty_mix.model_dump(),
                duration_minutes=spec.duration_minutes,
                sections=[sec.model_dump() for sec in spec.sections],
                sort_order=order,
            )
        )
        created += 1
    db.commit()
    return created
