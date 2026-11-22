import uuid

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Topic, TopicCategory, TopicGroup, User, UserRole
from app.seed.topic_library import TOPIC_LIBRARY, seed_topic_library

SPEC_TOPIC_COUNTS = [16, 14, 17, 15, 8, 19, 20, 16, 19, 10, 11, 14]


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded():
    with SessionLocal() as db:
        return seed_topic_library(db)


@pytest.fixture
def student(registered) -> dict:
    return h(registered["access_token"])


@pytest.fixture
def admin(client) -> dict:
    res = client.post(
        "/api/auth/register",
        json={"full_name": "Grace Admin", "email": "admin@example.com", "password": "adminpass1"},
    )
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == "admin@example.com")).one()
        user.role = UserRole.admin
        db.commit()
    return h(res.json()["access_token"])


def _find(tree: dict, topic_name: str) -> dict:
    for c in tree["categories"]:
        for g in c["groups"]:
            for t in g["topics"]:
                if t["name"] == topic_name:
                    return t
    raise AssertionError(topic_name)


# ---------- Seed ----------


def test_seed_matches_specification(seeded):
    assert (seeded.categories_created, seeded.topics_created) == (12, 179)
    with SessionLocal() as db:
        categories = db.scalars(select(TopicCategory).order_by(TopicCategory.sort_order)).all()
        assert [c.name for c in categories] == [name for name, _ in TOPIC_LIBRARY]
        assert [sum(len(g.topics) for g in c.groups) for c in categories] == SPEC_TOPIC_COUNTS
        patterns = next(c for c in categories if c.slug == "design-patterns")
        assert [g.name for g in patterns.groups] == ["Creational", "Structural", "Behavioral"]


def test_seed_is_idempotent_and_preserves_admin_edits(seeded):
    with SessionLocal() as db:
        topic = db.scalars(select(Topic).where(Topic.slug == "singleton")).one()
        topic.name = "Singleton Pattern"
        topic.is_active = False
        db.commit()
        again = seed_topic_library(db)
        assert vars(again) == {k: 0 for k in vars(again)}
        topic = db.scalars(select(Topic).where(Topic.slug == "singleton")).one()
        assert (topic.name, topic.is_active) == ("Singleton Pattern", False)
        assert db.query(Topic).count() == 179


# ---------- Student reads ----------


def test_topic_routes_require_authentication(client, seeded):
    for path in ["/api/topics", "/api/topics/categories", "/api/topics/search?q=x"]:
        assert client.get(path).status_code == 401


def test_tree_is_ordered_hierarchy(client, seeded, student):
    tree = client.get("/api/topics", headers=student).json()
    assert (tree["category_count"], tree["topic_count"]) == (12, 179)
    assert tree["group_count"] == sum(len(c["groups"]) for c in tree["categories"])
    first = tree["categories"][0]
    assert first["name"] == "OOP Fundamentals" and first["topic_count"] == 16
    assert [t["name"] for t in first["groups"][0]["topics"]][:2] == [
        "Procedural vs Object-Oriented Programming",
        "Classes and Objects",
    ]
    overriding, inheritance = _find(tree, "Method Overriding"), _find(tree, "Inheritance")
    assert inheritance["id"] in overriding["prerequisite_ids"]


def test_categories_summary(client, seeded, student):
    cats = client.get("/api/topics/categories", headers=student).json()
    assert [c["topic_count"] for c in cats] == SPEC_TOPIC_COUNTS
    assert "groups" not in cats[0]


def test_inactive_nodes_are_hidden_from_students(client, seeded, student):
    with SessionLocal() as db:
        db.scalars(select(Topic).where(Topic.slug == "singleton")).one().is_active = False
        db.scalars(select(TopicGroup).where(TopicGroup.slug == "structural")).one().is_active = False
        db.scalars(select(TopicCategory).where(TopicCategory.slug == "code-smells")).one().is_active = False
        db.commit()
    tree = client.get("/api/topics", headers=student).json()
    assert tree["category_count"] == 11
    assert tree["topic_count"] == 179 - 1 - 6 - 20
    names = {t["name"] for c in tree["categories"] for g in c["groups"] for t in g["topics"]}
    assert not {"Singleton", "Adapter", "Long Method"} & names
    assert client.get("/api/topics/search?q=adapter", headers=student).json()["total"] == 0


def test_search_ranks_name_matches_and_returns_paths(client, seeded, student):
    res = client.get("/api/topics/search?q=inheritance", headers=student).json()
    assert res["results"][0]["topic"]["name"] == "Inheritance"
    first = res["results"][0]
    assert first["group"]["name"] == "Inheritance" and first["category"]["name"] == "Four Pillars of OOP"
    names = [r["topic"]["name"] for r in res["results"]]
    assert "Composition over Inheritance" in names and "Replace Inheritance with Delegation" in names


def test_search_by_chapter_name_and_wildcards_are_literal(client, seeded, student):
    creational = client.get("/api/topics/search?q=creational", headers=student).json()
    assert creational["total"] == 5
    assert client.get("/api/topics/search?q=%25", headers=student).json()["total"] == 0
    assert client.get("/api/topics/search?q=_", headers=student).json()["total"] == 0
    assert client.get("/api/topics/search?q=%20%20", headers=student).status_code == 422
    assert client.get("/api/topics/search?q=class&limit=3", headers=student).json()["results"].__len__() == 3


def test_topic_detail(client, seeded, student):
    tree = client.get("/api/topics", headers=student).json()
    t = _find(tree, "Dynamic Method Dispatch")
    detail = client.get(f"/api/topics/{t['id']}", headers=student).json()
    assert detail["category"]["name"] == "Four Pillars of OOP"
    assert [p["name"] for p in detail["prerequisites"]] == ["Runtime Polymorphism"]
    assert client.get(f"/api/topics/{uuid.uuid4()}", headers=student).status_code == 404


def test_selection_expands_and_deduplicates(client, seeded, student):
    tree = client.get("/api/topics", headers=student).json()
    solid = next(c for c in tree["categories"] if c["slug"] == "solid-principles")
    patterns = next(c for c in tree["categories"] if c["slug"] == "design-patterns")
    creational = patterns["groups"][0]
    body = {
        "category_ids": [solid["id"]],
        "group_ids": [creational["id"]],
        "topic_ids": [creational["topics"][0]["id"], _find(tree, "Observer")["id"]],
    }
    res = client.post("/api/topics/selection", json=body, headers=student).json()
    assert res["topic_count"] == 8 + 5 + 1
    assert len(set(res["topic_ids"])) == res["topic_count"]
    summary = {c["slug"]: (c["selected_topic_count"], c["total_topic_count"]) for c in res["categories"]}
    assert summary == {"solid-principles": (8, 8), "design-patterns": (6, 19)}
    assert res["topics"][0]["category"]["slug"] == "solid-principles"


def test_selection_validation(client, seeded, student):
    assert client.post("/api/topics/selection", json={}, headers=student).status_code == 422
    res = client.post("/api/topics/selection", json={"topic_ids": [str(uuid.uuid4())]}, headers=student)
    assert res.status_code == 422


# ---------- Admin ----------


def test_admin_routes_reject_students(client, seeded, student):
    assert client.get("/api/admin/topics/tree", headers=student).status_code == 403
    res = client.post("/api/admin/topics/categories", json={"name": "Sneaky"}, headers=student)
    assert res.status_code == 403


def test_admin_create_edit_deactivate(client, seeded, admin):
    cat = client.post("/api/admin/topics/categories", json={"name": "  Concurrency   Basics "}, headers=admin).json()
    assert (cat["name"], cat["slug"], cat["sort_order"]) == ("Concurrency Basics", "concurrency-basics", 12)
    dup = client.post("/api/admin/topics/categories", json={"name": "Concurrency Basics"}, headers=admin)
    assert dup.status_code == 409

    group = client.post(
        "/api/admin/topics/groups", json={"category_id": cat["id"], "name": "Threads"}, headers=admin
    ).json()
    topic = client.post(
        "/api/admin/topics",
        json={"group_id": group["id"], "name": "Thread Safety", "description": "Shared state."},
        headers=admin,
    )
    assert topic.status_code == 201, topic.text
    topic = topic.json()
    assert topic["category"]["slug"] == "concurrency-basics" and topic["sort_order"] == 0

    edited = client.patch(f"/api/admin/topics/{topic['id']}", json={"name": "Thread-Safe Classes"}, headers=admin)
    assert edited.json()["name"] == "Thread-Safe Classes" and edited.json()["slug"] == "thread-safety"
    assert client.patch(f"/api/admin/topics/{topic['id']}", json={"name": None}, headers=admin).status_code == 422

    client.patch(f"/api/admin/topics/categories/{cat['id']}", json={"is_active": False}, headers=admin)
    student_tree = client.get("/api/topics", headers=admin).json()
    assert student_tree["category_count"] == 12
    admin_tree = client.get("/api/admin/topics/tree", headers=admin).json()
    assert admin_tree["category_count"] == 13
    assert admin_tree["categories"][-1]["is_active"] is False


def test_admin_move_and_reorder(client, seeded, admin):
    tree = client.get("/api/admin/topics/tree", headers=admin).json()
    patterns = next(c for c in tree["categories"] if c["slug"] == "design-patterns")
    creational, structural = patterns["groups"][0], patterns["groups"][1]
    singleton = creational["topics"][0]

    moved = client.patch(
        f"/api/admin/topics/{singleton['id']}", json={"group_id": structural["id"]}, headers=admin
    ).json()
    assert moved["sort_order"] == len(structural["topics"])

    ids = [t["id"] for t in creational["topics"][1:]][::-1]
    assert client.put(f"/api/admin/topics/groups/{creational['id']}/topics/order", json={"ids": ids}, headers=admin)
    tree = client.get("/api/admin/topics/tree", headers=admin).json()
    patterns = next(c for c in tree["categories"] if c["slug"] == "design-patterns")
    assert [t["id"] for t in patterns["groups"][0]["topics"]] == ids

    partial = client.put(
        f"/api/admin/topics/groups/{creational['id']}/topics/order", json={"ids": ids[:2]}, headers=admin
    )
    assert partial.status_code == 422

    cat_ids = [c["id"] for c in tree["categories"]][::-1]
    assert client.put("/api/admin/topics/categories/order", json={"ids": cat_ids}, headers=admin).status_code == 204
    cats = client.get("/api/topics/categories", headers=admin).json()
    assert cats[0]["name"] == "Testing and Maintainability"

    group_ids = [g["id"] for g in patterns["groups"]][::-1]
    res = client.put(
        f"/api/admin/topics/categories/{patterns['id']}/groups/order", json={"ids": group_ids}, headers=admin
    )
    assert res.status_code == 204


def test_admin_prerequisites_reject_self_and_cycles(client, seeded, admin):
    tree = client.get("/api/admin/topics/tree", headers=admin).json()
    inheritance, overriding = _find(tree, "Inheritance"), _find(tree, "Method Overriding")
    dispatch = _find(tree, "Dynamic Method Dispatch")
    url = f"/api/admin/topics/{inheritance['id']}/prerequisites"

    assert client.put(url, json={"prerequisite_ids": [inheritance["id"]]}, headers=admin).status_code == 422
    # Inheritance <- Method Overriding <- Runtime Polymorphism <- Dynamic Method Dispatch
    cycle = client.put(url, json={"prerequisite_ids": [dispatch["id"]]}, headers=admin)
    assert cycle.status_code == 422 and "circular" in cycle.json()["detail"]
    unknown = client.put(url, json={"prerequisite_ids": [str(uuid.uuid4())]}, headers=admin)
    assert unknown.status_code == 422

    ok = client.put(f"/api/admin/topics/{overriding['id']}/prerequisites", json={"prerequisite_ids": []}, headers=admin)
    assert ok.status_code == 200 and ok.json()["prerequisites"] == []
    assert client.put(url, json={"prerequisite_ids": [dispatch["id"]]}, headers=admin).status_code == 200


def test_admin_seed_endpoint_is_idempotent(client, admin):
    first = client.post("/api/admin/topics/seed", headers=admin).json()
    assert first["topics_created"] == 179
    assert client.post("/api/admin/topics/seed", headers=admin).json()["topics_created"] == 0


def test_reseed_keeps_removed_prerequisites_removed(client, seeded, admin):
    tree = client.get("/api/admin/topics/tree", headers=admin).json()
    overriding = _find(tree, "Method Overriding")
    client.put(f"/api/admin/topics/{overriding['id']}/prerequisites", json={"prerequisite_ids": []}, headers=admin)
    assert client.post("/api/admin/topics/seed", headers=admin).json()["prerequisites_created"] == 0
    assert client.get(f"/api/admin/topics/{overriding['id']}", headers=admin).json()["prerequisites"] == []


def test_create_requires_slug_when_name_has_no_ascii(client, seeded, admin):
    res = client.post("/api/admin/topics/categories", json={"name": "多态"}, headers=admin)
    assert res.status_code == 422 and "slug" in res.json()["detail"]
    ok = client.post("/api/admin/topics/categories", json={"name": "多态", "slug": "polymorphism-zh"}, headers=admin)
    assert ok.status_code == 201
