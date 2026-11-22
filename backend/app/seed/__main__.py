"""Seed the OOC topic library: `python -m app.seed`."""

from app.db import SessionLocal
from app.seed.topic_library import seed_topic_library


def main() -> None:
    with SessionLocal() as db:
        counts = seed_topic_library(db)
    print(
        f"Topic library seeded: {counts.categories_created} categories, {counts.groups_created} chapters, "
        f"{counts.topics_created} topics, {counts.prerequisites_created} prerequisites created."
    )


if __name__ == "__main__":
    main()
