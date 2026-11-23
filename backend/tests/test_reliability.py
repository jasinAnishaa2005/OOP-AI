# ruff: noqa: F811  (fixtures are imported from test_exams)
"""Restart recovery, daily-limit accounting, shared rate limits and concurrent requests (SQLite and PostgreSQL)."""

import threading
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.ai.base import GenerationError
from app.config import get_settings
from app.core.rate_limit import RateLimiter, limiter
from app.core.time import utcnow
from app.db import SessionLocal
from app.models import Exam, ExamGenerationRequest, ExamQuestion, RateLimitBucket
from app.services import exam_generation
from app.services.exam_generation import recover_stuck_exams, run_generation
from app.services.generation_worker import GenerationRecovery
from tests.test_exams import ScriptedGenerator, custom, other, provider, sec, seeded, student, topic_ids  # noqa: F401


def body() -> dict:
    return custom({"topic_ids": topic_ids("Coupling")}, [sec("mcq", 2, 1)])


def _ledger(exam_id: str | uuid.UUID) -> list[str]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(ExamGenerationRequest.outcome).where(ExamGenerationRequest.exam_id == uuid.UUID(str(exam_id)))
            )
        )


def _simulate_crash(exam_id: str, status: str, age: timedelta, runs: int = 1) -> None:
    """Leave the exam as a killed worker would: mid-generation (or never started), no questions stored."""
    with SessionLocal() as db:
        db.execute(
            update(Exam)
            .where(Exam.id == uuid.UUID(exam_id))
            .values(status=status, generation_id=uuid.uuid4(), generation_runs=runs, updated_at=utcnow() - age)
        )
        db.query(ExamQuestion).filter(ExamQuestion.exam_id == uuid.UUID(exam_id)).delete()
        db.execute(
            update(ExamGenerationRequest)
            .where(ExamGenerationRequest.exam_id == uuid.UUID(exam_id))
            .values(outcome="pending")
        )
        db.commit()


def _new_exam(client, student) -> str:
    res = client.post("/api/exams", json=body(), headers=student)
    assert res.status_code == 202, res.text
    return res.json()["id"]


# ---------- Daily-limit accounting ----------


def test_ledger_outcomes_follow_generation(client, seeded, student, provider):
    provider(ScriptedGenerator(GenerationError("down", retryable=False)))
    failed = _new_exam(client, student)
    ready = _new_exam(client, student)
    assert _ledger(failed) == ["failed"] and _ledger(ready) == ["succeeded"]
    client.post(f"/api/exams/{failed}/retry", headers=student)
    assert sorted(_ledger(failed)) == ["failed", "succeeded"]


def test_incomplete_generation_holds_its_slot_until_it_finishes(client, seeded, student, monkeypatch):
    """A pending/generating exam counts, so parallel requests cannot overshoot the limit while AI calls run."""
    monkeypatch.setattr(get_settings(), "exam_daily_limit", 1)
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(seconds=0))
    assert client.post("/api/exams", json=body(), headers=student).status_code == 429
    exam_generation._fail(uuid.UUID(exam_id), "boom")
    assert _ledger(exam_id) == ["failed"]
    assert client.post("/api/exams", json=body(), headers=student).status_code == 202


def test_successful_exam_still_counts_after_deletion(client, seeded, student, monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_daily_limit", 1)
    exam_id = _new_exam(client, student)
    assert client.delete(f"/api/exams/{exam_id}", headers=student).status_code == 204
    with SessionLocal() as db:
        assert db.scalars(select(ExamGenerationRequest.outcome)).all() == ["succeeded"]
    assert client.post("/api/exams", json=body(), headers=student).status_code == 429


def test_retrying_a_stuck_exam_releases_the_abandoned_run(client, seeded, student, monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_daily_limit", 1)
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=2))
    assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 202
    assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready"
    assert sorted(_ledger(exam_id)) == ["failed", "succeeded"]


def test_concurrent_creations_cannot_exceed_daily_limit(client, seeded, student, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(get_settings(), "exam_daily_limit", 3)
    monkeypatch.setattr(get_settings(), "exam_create_rate_limit", "100/minute")
    payload = body()
    statuses: list[int] = []
    barrier = threading.Barrier(8)

    def post() -> None:
        with TestClient(app) as c:
            barrier.wait()
            statuses.append(c.post("/api/exams", json=payload, headers=student).status_code)

    threads = [threading.Thread(target=post) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [202] * 3 + [429] * 5
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Exam)) == 3
        assert db.scalar(select(func.count()).select_from(ExamGenerationRequest)) == 3


# ---------- Restart recovery ----------


def test_recovery_regenerates_exam_abandoned_mid_generation(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=1))
    assert recover_stuck_exams() == [uuid.UUID(exam_id)]
    run_generation(uuid.UUID(exam_id), ScriptedGenerator())
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    assert exam["status"] == "ready" and len(exam["questions"]) == 2
    assert _ledger(exam_id) == ["succeeded"]


def test_recovery_starts_pending_exam_that_was_never_claimed(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "pending", timedelta(minutes=10), runs=0)
    assert recover_stuck_exams() == [uuid.UUID(exam_id)]


def test_recovery_leaves_live_generations_alone(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(seconds=30))
    recent_pending = _new_exam(client, student)
    _simulate_crash(recent_pending, "pending", timedelta(seconds=5), runs=0)
    assert recover_stuck_exams() == []
    with SessionLocal() as db:
        assert db.get(Exam, uuid.UUID(exam_id)).status == "generating"


def test_recovery_gives_up_after_max_runs_and_releases_quota(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=1), runs=get_settings().generation_max_runs)
    assert recover_stuck_exams() == []
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    assert exam["status"] == "failed" and "interrupted" in exam["failure_reason"]
    assert _ledger(exam_id) == ["failed"]
    assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 202
    assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready"


def test_stale_worker_cannot_overwrite_recovered_run(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=1))
    with SessionLocal() as db:
        stale_run = db.get(Exam, uuid.UUID(exam_id)).generation_id
    recover_stuck_exams()
    run_generation(uuid.UUID(exam_id), ScriptedGenerator())
    exam_generation._fail(uuid.UUID(exam_id), "late failure from the old worker", stale_run)
    assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready"


def test_parallel_sweepers_generate_each_exam_once(client, seeded, student):
    """Several API workers restarting together all sweep; claiming keeps it to one generation per exam."""
    exams = [_new_exam(client, student) for _ in range(3)]
    for exam_id in exams:
        _simulate_crash(exam_id, "generating", timedelta(hours=1))
    gen = ScriptedGenerator()
    barrier = threading.Barrier(4)

    def worker() -> None:
        barrier.wait()
        for exam_id in recover_stuck_exams():
            run_generation(exam_id, gen)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(gen.requests) == 3  # one mcq batch per exam
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ExamQuestion)) == 6
    for exam_id in exams:
        assert _ledger(exam_id) == ["succeeded"]


def test_recovery_worker_sweeps_on_startup(client, seeded, student, monkeypatch):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=1))
    recovery = GenerationRecovery()
    recovery.start()  # first sweep runs immediately, as after a restart
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready":
                break
            time.sleep(0.1)
        assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready"
    finally:
        recovery.stop()


# ---------- Shared rate limits ----------


def test_rate_limit_counters_are_shared_between_workers():
    worker_a, worker_b = RateLimiter(), RateLimiter()
    results = [w.hit("t", "student-1", "3/minute") for w in (worker_a, worker_b, worker_a, worker_b)]
    assert results[:3] == [None, None, None] and results[3] is not None and 0 < results[3] <= 60
    with SessionLocal() as db:
        keys = db.scalars(select(RateLimitBucket.key)).all()
    assert len(keys) == 1 and "student-1" not in keys[0]  # only a hash is stored


def test_concurrent_hits_are_counted_exactly():
    barrier = threading.Barrier(10)
    results: list[int | None] = []

    def hit() -> None:
        barrier.wait()
        results.append(RateLimiter().hit("t", "burst", "4/minute"))

    threads = [threading.Thread(target=hit) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(None) == 4
    with SessionLocal() as db:
        assert db.scalar(select(RateLimitBucket.count)) == 10


def test_expired_windows_are_purged():
    limiter.hit("t", "old", "1/second")
    with SessionLocal() as db:
        db.execute(update(RateLimitBucket).values(expires_at=0))
        db.commit()
    limiter.purge_expired()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(RateLimitBucket)) == 0


def test_campus_network_students_are_limited_per_account(client):
    """Students behind one campus IP each keep their own login budget; one account is still locked out."""
    for n in range(15):
        reg = {"full_name": f"S {n}", "email": f"s{n}@uni.edu", "student_id": f"ID-{n}", "password": "objects4ever"}
        assert client.post("/api/auth/register", json=reg).status_code == 201
    logins = [
        client.post("/api/auth/login", json={"identifier": f"s{n}@uni.edu", "password": "objects4ever"}).status_code
        for n in range(15)
    ]
    assert logins == [200] * 15
    guesses = [
        client.post("/api/auth/login", json={"identifier": "s0@uni.edu", "password": "wrong-pass1"}).status_code
        for _ in range(12)
    ]
    assert guesses[-1] == 429
    res = client.post("/api/auth/login", json={"identifier": "s1@uni.edu", "password": "objects4ever"})
    assert res.status_code == 200


def test_rate_limited_response_has_retry_after(client, registered):
    for _ in range(11):
        res = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "wrong-pass1"})
    assert res.status_code == 429 and int(res.headers["Retry-After"]) >= 1


def test_ip_limit_still_stops_floods(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_ip_rate_limit", "5/minute")
    statuses = [
        client.post("/api/auth/login", json={"identifier": f"u{n}@x.edu", "password": "wrong-pass1"}).status_code
        for n in range(7)
    ]
    assert statuses[-2:] == [429, 429]


def test_exam_rate_limit_is_per_student_not_per_ip(client, seeded, student, other, monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_create_rate_limit", "2/minute")
    mine = [client.post("/api/exams", json=body(), headers=student).status_code for _ in range(3)]
    theirs = client.post("/api/exams", json=body(), headers=other).status_code
    assert mine == [202, 202, 429] and theirs == 202


def test_invalid_rate_limit_setting_is_rejected():
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(exam_create_rate_limit="lots")


# ---------- Idempotency ----------


def test_idempotency_key_reused_for_different_request_is_rejected(client, seeded, student):
    key = {"Idempotency-Key": "k1"}
    assert client.post("/api/exams", json=body(), headers=student | key).status_code == 202
    other_body = custom({"topic_ids": topic_ids("Cohesion")}, [sec("mcq", 2, 1)])
    res = client.post("/api/exams", json=other_body, headers=student | key)
    assert res.status_code == 409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Exam)) == 1
        assert db.scalar(select(func.count()).select_from(ExamGenerationRequest)) == 1


def test_concurrent_duplicate_requests_create_one_exam(client, seeded, student):
    from fastapi.testclient import TestClient

    from app.main import app

    payload = body()
    ids: list[str] = []
    barrier = threading.Barrier(6)

    def post() -> None:
        with TestClient(app) as c:
            barrier.wait()
            res = c.post("/api/exams", json=payload, headers=student | {"Idempotency-Key": "double-tap"})
            assert res.status_code == 202, res.text
            ids.append(res.json()["id"])

    threads = [threading.Thread(target=post) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(ids)) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Exam)) == 1
        assert db.scalar(select(func.count()).select_from(ExamGenerationRequest)) == 1
        assert db.scalar(select(func.count()).select_from(ExamQuestion)) == 2
