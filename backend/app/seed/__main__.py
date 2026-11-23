"""Seed the OOC topic library and preset exam templates: `python -m app.seed`."""

from app.db import SessionLocal
from app.seed.exam_templates import seed_exam_templates
from app.seed.topic_library import seed_topic_library


def main() -> None:
    with SessionLocal() as db:
        counts = seed_topic_library(db)
        templates = seed_exam_templates(db)
    print(
        f"Topic library seeded: {counts.categories_created} categories, {counts.groups_created} chapters, "
        f"{counts.topics_created} topics, {counts.prerequisites_created} prerequisites created."
    )
    print(f"Exam templates seeded: {templates} created.")


if __name__ == "__main__":
    main()
