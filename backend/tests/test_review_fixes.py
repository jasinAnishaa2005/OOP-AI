# ruff: noqa: F811  (fixtures are imported from test_exams)
"""Regression tests for the Devin Review findings on the reliability changes."""

import threading
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.genai import errors
from pydantic import ValidationError
from sqlalchemy import event, func, select, update

from app.ai.base import GenerationError, GenerationRequest
from app.api.routes import auth as auth_routes
from app.config import Settings, get_settings, parse_limit
from app.core.time import utcnow
from app.db import SessionLocal, engine
from app.main import app
from app.models import Exam, ExamGenerationAttempt, ExamQuestion
from app.services import exam_generation
from app.services import exams as exams_service
from app.services.exam_generation import generation_lease, recover_stuck_exams, run_generation
from tests.test_exams import ScriptedGenerator, provider, seeded, student  # noqa: F401
from tests.test_reliability import _ledger, _new_exam, _simulate_crash, body

PASSWORD = "objects4ever"
REQUEST = GenerationRequest(
    question_type="mcq", system_instruction="sys", prompt="p", response_schema={"type": "object"}
)


@pytest.fixture
def ip_from_header(monkeypatch):
    """Let each test request claim its own client IP."""
    monkeypatch.setattr(auth_routes, "client_ip", lambda request: request.headers.get("x-test-ip", "testclient"))


def login(client, identifier: str, password: str, ip: str = "10.0.0.1") -> int:
    body = {"identifier": identifier, "password": password}
    return client.post("/api/auth/login", json=body, headers={"x-test-ip": ip}).status_code


# ---------- Finding 1: email and student ID share one account budget ----------


def test_email_and_student_id_share_one_login_budget(client, registered, ip_from_header):
    identifiers = ["ada@example.com", "CSE-2024-001"] * 6
    statuses = [login(client, ident, "wrong-pass1") for ident in identifiers]
    assert statuses[:10] == [401] * 10 and statuses[10:] == [429, 429]


def test_identifier_spelling_does_not_split_the_budget(client, ip_from_header):
    variants = ["ghost@uni.edu", "GHOST@uni.edu", " ghost@uni.edu "] * 4
    statuses = [login(client, v, "wrong-pass1") for v in variants]
    assert statuses[10:] == [429, 429]


# ---------- Finding 2: deliberate lockout ----------


def test_attacker_on_another_network_cannot_lock_student_out(client, registered, ip_from_header):
    attacker = [login(client, "ada@example.com", "wrong-pass1", ip="203.0.113.9") for _ in range(12)]
    assert attacker[-1] == 429
    assert login(client, "ada@example.com", PASSWORD, ip="10.0.0.1") == 200


def test_successful_logins_do_not_use_the_budget(client, registered, ip_from_header):
    assert [login(client, "ada@example.com", PASSWORD) for _ in range(15)] == [200] * 15
    assert login(client, "ada@example.com", "wrong-pass1") == 401


def test_distributed_guessing_is_capped_per_account(client, registered, ip_from_header, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_account_rate_limit", "5/hour")
    statuses = [login(client, "CSE-2024-001", "wrong-pass1", ip=f"198.51.100.{n}") for n in range(7)]
    assert statuses == [401] * 5 + [429, 429]


# ---------- Finding 3: one database connection per rate-limited request ----------


@pytest.fixture
def connections():
    """Peak number of pooled connections one request holds at the same time."""
    state = {"in_use": 0, "peak": 0}

    def on_checkout(*_):
        state["in_use"] += 1
        state["peak"] = max(state["peak"], state["in_use"])

    def on_checkin(*_):
        state["in_use"] -= 1

    event.listen(engine, "checkout", on_checkout)
    event.listen(engine, "checkin", on_checkin)
    yield state
    event.remove(engine, "checkout", on_checkout)
    event.remove(engine, "checkin", on_checkin)


def test_rate_limited_login_uses_the_request_connection(client, registered, connections):
    connections["peak"] = connections["in_use"]
    assert client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "x1"}).status_code == 401
    assert connections["peak"] == 1


def test_rate_limited_exam_request_uses_the_request_connection(client, seeded, student, connections):
    exam_id = _new_exam(client, student)  # ready, so the retry below is refused without starting a background run
    connections["peak"] = connections["in_use"]
    assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 409
    assert connections["peak"] == 1


def test_rate_limited_requests_work_with_a_one_connection_pool(client, registered, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db import get_db

    tiny = create_engine(engine.url, pool_size=1, max_overflow=0, pool_timeout=2)
    if tiny.dialect.name == "sqlite":
        event.listen(tiny, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    tiny_sessions = sessionmaker(bind=tiny, autoflush=False, expire_on_commit=False)

    def tiny_db():
        with tiny_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = tiny_db
    try:
        assert login(client, "ada@example.com", PASSWORD) == 200
        assert login(client, "ada@example.com", "wrong-pass1") == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
        tiny.dispose()


# ---------- Finding 4: a recovery sweep never cancels a fresh retry ----------


def test_sweep_does_not_fail_a_retry_started_after_it_looked(client, seeded, student, monkeypatch):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "generating", timedelta(hours=2), runs=get_settings().generation_max_runs)
    from app.api.routes import exams as exam_routes

    queued = []
    monkeypatch.setattr(exam_routes, "run_generation", lambda *args: queued.append(args))
    real_fail = exam_generation._fail

    def retry_then_fail(*args, **kwargs):
        # The student retries between the sweep's SELECT and its UPDATE; the retry's run is still queued.
        assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 202
        return real_fail(*args, **kwargs)

    monkeypatch.setattr(exam_generation, "_fail", retry_then_fail)
    assert recover_stuck_exams() == []
    assert len(queued) == 1
    run_generation(*queued[0])
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    assert exam["status"] == "ready" and exam["failure_reason"] is None
    assert sorted(_ledger(exam_id)) == ["failed", "succeeded"]


def test_sweep_still_fails_exams_that_stay_abandoned(client, seeded, student):
    exam_id = _new_exam(client, student)
    _simulate_crash(exam_id, "pending", timedelta(hours=2), runs=get_settings().generation_max_runs)
    assert recover_stuck_exams() == []
    assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "failed"
    assert _ledger(exam_id) == ["failed"]


# ---------- Finding 5: fallback models are included in the lease ----------


@pytest.fixture
def gemini_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_model", "primary")
    monkeypatch.setattr(settings, "gemini_fallback_models", "fallback-a, fallback-b, primary")
    monkeypatch.setattr(settings, "ai_timeout_seconds", 300)
    monkeypatch.setattr(settings, "ai_max_attempts", 3)
    monkeypatch.setattr(settings, "ai_retry_backoff_seconds", 10.0)
    monkeypatch.setattr(settings, "generation_lease_seconds", 900)
    return settings


def test_lease_covers_every_model_in_one_attempt(gemini_settings):
    # 3 distinct models x 300 s timeout + backoff + margin; the old formula gave 900 s.
    assert generation_lease() >= timedelta(seconds=3 * 300 + 10 * 3)


def test_slow_healthy_fallback_run_is_not_recovered(client, seeded, student, provider, request):
    from app.ai.fake import FakeGenerator

    provider(FakeGenerator())  # offline generator; the Gemini settings below only shape the lease
    exam_id = _new_exam(client, student)
    request.getfixturevalue("gemini_settings")
    _simulate_crash(exam_id, "generating", timedelta(seconds=950))  # quieter than 900 s, within one attempt
    assert recover_stuck_exams() == []
    with SessionLocal() as db:
        assert db.scalar(select(Exam.status).where(Exam.id == uuid.UUID(exam_id))) == "generating"
    # ...and a student cannot restart it either, so it is never generated twice.
    assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 409


def test_fake_provider_lease_ignores_gemini_fallbacks(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_provider", "fake")
    monkeypatch.setattr(settings, "generation_lease_seconds", 1)
    expected = settings.ai_timeout_seconds + settings.ai_retry_backoff_seconds * settings.ai_max_attempts + 60
    assert generation_lease() == timedelta(seconds=expected)


# ---------- Finding 6: retry and completion lock rows in the same order ----------


def test_retry_racing_a_finishing_run_waits_instead_of_deadlocking(client, seeded, student, monkeypatch):
    exam_id = _new_exam(client, student)
    with SessionLocal() as db:
        db.execute(update(Exam).where(Exam.id == uuid.UUID(exam_id)).values(status="pending", updated_at=utcnow()))
        db.commit()
    _simulate_crash(exam_id, "pending", timedelta(0), runs=0)
    # Make the running exam look abandoned to the retry, so it tries to take it over mid-completion.
    monkeypatch.setattr(exams_service, "generation_lease", lambda *_: timedelta(seconds=-60))
    exam_locked = threading.Event()
    real_settle = exam_generation._settle_usage

    def slow_settle(db, eid, outcome):
        if outcome == "succeeded":  # completion holds the exam row lock here
            exam_locked.set()
            time.sleep(1.5)
        real_settle(db, eid, outcome)

    monkeypatch.setattr(exam_generation, "_settle_usage", slow_settle)
    errors: list[BaseException] = []

    def finish() -> None:
        try:
            run_generation(uuid.UUID(exam_id), ScriptedGenerator())
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    worker = threading.Thread(target=finish)
    worker.start()
    assert exam_locked.wait(10)
    with TestClient(app) as c:
        res = c.post(f"/api/exams/{exam_id}/retry", headers=student)
    worker.join(20)
    assert not errors
    assert res.status_code == 409, res.text  # the retry saw the finished exam after waiting for its lock
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    assert exam["status"] == "ready" and len(exam["questions"]) == 2
    assert _ledger(exam_id) == ["succeeded"]


def test_concurrent_retries_of_a_failed_exam_start_one_run(client, seeded, student, monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_create_rate_limit", "100/minute")
    exam_id = _new_exam(client, student)
    with SessionLocal() as db:
        db.execute(update(Exam).where(Exam.id == uuid.UUID(exam_id)).values(status="failed"))
        db.commit()
    barrier = threading.Barrier(6)
    statuses: list[int] = []

    def retry() -> None:
        with TestClient(app) as c:
            barrier.wait()
            statuses.append(c.post(f"/api/exams/{exam_id}/retry", headers=student).status_code)

    threads = [threading.Thread(target=retry) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(statuses) == [202] + [409] * 5
    assert client.get(f"/api/exams/{exam_id}", headers=student).json()["status"] == "ready"


# ---------- Finding 7: zero or negative rate-limit periods ----------


@pytest.mark.parametrize(
    "limit", ["10 per 0 minutes", "10/0 minute", "0/minute", "-5/minute", "10/-1 minute", "10 per -2 hours", ""]
)
def test_invalid_rate_limit_periods_are_rejected_at_startup(limit):
    with pytest.raises(ValueError):
        parse_limit(limit)
    for field in ("auth_rate_limit", "auth_account_rate_limit", "auth_ip_rate_limit", "exam_create_rate_limit"):
        with pytest.raises(ValidationError):
            Settings(**{field: limit})


@pytest.mark.parametrize(
    ("limit", "parsed"), [("10/minute", (10, 60)), ("5 per 2 hours", (5, 7200)), ("1/second", (1, 1))]
)
def test_valid_rate_limits_still_parse(limit, parsed):
    assert parse_limit(limit) == parsed


def test_tests_never_reach_the_real_gemini_api(client, seeded, student, gemini_settings):
    assert not gemini_settings.gemini_api_key.get_secret_value()
    res = client.post("/api/exams", json=body(), headers=student)
    assert res.status_code == 503


# ---------- Second review: rejected sign-ins must not fill the login budget ----------


def test_rejected_requests_are_not_counted_so_a_refund_frees_a_slot():
    """The limit was full when a legitimate request and a rejected one arrived together; the refund must free a slot."""
    from app.core.rate_limit import RateLimiter

    worker = RateLimiter()
    with SessionLocal() as db:
        charged = [worker.enforce(db, "t", "acct", "3/minute") for _ in range(3)]
        with pytest.raises(HTTPException) as info:
            worker.enforce(db, "t", "acct", "3/minute")
        assert info.value.status_code == 429
        worker.refund(db, charged[-1])  # the third request turned out to be a correct password
        assert worker.enforce(db, "t", "acct", "3/minute") is not None


def test_correct_password_is_not_blocked_by_a_guess_rejected_meanwhile(client, registered, ip_from_header, monkeypatch):
    for _ in range(9):
        assert login(client, "ada@example.com", "wrong-pass1") == 401
    real_authenticate = auth_routes.auth_service.authenticate
    injected = []

    def guess_arrives_meanwhile(db, identifier, password, user=None):
        if password == PASSWORD and not injected:
            injected.append(login(client, "ada@example.com", "wrong-pass1"))  # budget full: rejected
        return real_authenticate(db, identifier, password, user)

    monkeypatch.setattr(auth_routes.auth_service, "authenticate", guess_arrives_meanwhile)
    assert login(client, "ada@example.com", PASSWORD) == 200
    assert injected == [429]
    assert login(client, "ada@example.com", PASSWORD) == 200


def test_failed_logins_still_block_even_a_correct_password(client, registered, ip_from_header):
    assert [login(client, "ada@example.com", "wrong-pass1") for _ in range(10)] == [401] * 10
    assert login(client, "ada@example.com", "wrong-pass1") == 429
    assert login(client, "ada@example.com", PASSWORD) == 429  # brute-force protection is unchanged


def test_account_cap_rejection_does_not_spend_the_network_budget(client, registered, ip_from_header, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_account_rate_limit", "3/hour")
    assert [login(client, "ada@example.com", "wrong-pass1") for _ in range(4)] == [401] * 3 + [429]
    monkeypatch.setattr(settings, "auth_account_rate_limit", "100/hour")
    # Only the 3 checked passwords count against this network's 10, not the one rejected by the account cap.
    assert [login(client, "ada@example.com", "wrong-pass1") for _ in range(8)] == [401] * 7 + [429]


# ---------- Second review: hard wall-clock limit on Gemini requests ----------


class SlowModels:
    """An offline stand-in for the Gemini client whose replies arrive after `delay` seconds (or raise)."""

    def __init__(self, delay: float, outcome=None):
        self.delay, self.outcome = delay, outcome
        self.started = 0
        self.finished = threading.Event()

    def generate_content(self, **kwargs):
        self.started += 1
        time.sleep(self.delay)
        self.finished.set()
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome or SimpleNamespace(text='{"questions": []}', usage_metadata=None)


def slow_gemini(delay: float, timeout: float = 0.2, outcome=None):
    from app.ai.gemini import GeminiGenerator

    models = SlowModels(delay, outcome)
    return GeminiGenerator("unused", "gemini-test", timeout, client=SimpleNamespace(models=models)), models


def test_slow_gemini_reply_times_out_and_the_exam_is_retryable(client, seeded, student, provider):
    generator, models = slow_gemini(delay=1.0)
    provider(generator)
    started = time.monotonic()
    exam_id = _new_exam(client, student)
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    assert time.monotonic() - started < 5
    assert exam["status"] == "failed" and "unavailable" in exam["failure_reason"]
    assert models.started == get_settings().ai_max_attempts  # retry limit unchanged
    with SessionLocal() as db:
        outcomes = db.scalars(
            select(ExamGenerationAttempt.outcome).where(ExamGenerationAttempt.exam_id == uuid.UUID(exam_id))
        ).all()
    assert outcomes == ["timeout"] * get_settings().ai_max_attempts
    assert _ledger(exam_id) == ["failed"]  # a timed-out exam does not use up the daily limit

    # The late replies arrive after the deadline and are discarded: nothing is stored, nothing is regenerated.
    models.finished.wait(5)
    time.sleep(1.2)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ExamQuestion)) == 0
    from app.ai.fake import FakeGenerator

    provider(FakeGenerator())
    assert client.post(f"/api/exams/{exam_id}/retry", headers=student).status_code == 202
    exam = client.get(f"/api/exams/{exam_id}", headers=student).json()
    with SessionLocal() as db:
        stored = db.scalar(select(func.count()).select_from(ExamQuestion))
    assert exam["status"] == "ready" and stored == len(exam["questions"])


def test_late_reply_is_never_returned():
    generator, models = slow_gemini(delay=0.5)
    with pytest.raises(GenerationError) as info:
        generator.generate(REQUEST)
    assert info.value.kind == "timeout" and info.value.retryable
    assert models.finished.wait(2)  # the reply did come, after the caller had already moved on


def test_fallback_after_a_slow_overloaded_primary_stays_within_the_overall_limit():
    from app.ai.gemini import GeminiGenerator

    busy = errors.APIError(503, {"error": {"message": "busy"}})

    class Models:
        calls: list[str] = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs["model"])
            time.sleep(0.15 if kwargs["model"] == "a" else 1.0)
            if kwargs["model"] == "a":
                raise busy
            return SimpleNamespace(text="{}", usage_metadata=None)

    models = Models()
    generator = GeminiGenerator("unused", "a", 0.2, client=SimpleNamespace(models=models), fallback_models=("b",))
    started = time.monotonic()
    with pytest.raises(GenerationError) as info:
        generator.generate(REQUEST)
    assert models.calls == ["a", "b"] and info.value.kind == "timeout"
    assert time.monotonic() - started < 0.2 * 2 + 0.15


def test_fallback_still_succeeds_within_the_limit():
    from app.ai.gemini import GeminiGenerator

    class Models:
        def generate_content(self, **kwargs):
            time.sleep(0.05)
            if kwargs["model"] == "a":
                raise errors.APIError(503, {"error": {"message": "busy"}})
            return SimpleNamespace(text='{"questions": []}', usage_metadata=None)

    generator = GeminiGenerator("unused", "a", 0.5, client=SimpleNamespace(models=Models()), fallback_models=("b",))
    assert generator.generate(REQUEST).model == "b"


def test_lease_outlasts_the_longest_possible_gemini_request(gemini_settings):
    from app.ai.gemini import GeminiGenerator

    generator = GeminiGenerator(
        "unused",
        gemini_settings.gemini_model,
        gemini_settings.ai_timeout_seconds,
        client=SimpleNamespace(models=None),
        fallback_models=gemini_settings.gemini_fallback_model_list,
    )
    longest_request = generator.timeout_seconds * len(generator.models)
    longest_gap = longest_request + gemini_settings.ai_retry_backoff_seconds * gemini_settings.ai_max_attempts
    assert generation_lease() > timedelta(seconds=longest_gap)


def test_zero_ai_timeout_is_rejected_at_startup():
    with pytest.raises(ValidationError):
        Settings(ai_timeout_seconds=0)


def test_a_primary_that_keeps_timing_out_falls_back_to_a_healthy_model():
    from app.ai.gemini import GeminiGenerator

    class Models:
        calls: list[str] = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs["model"])
            if kwargs["model"] == "a":
                time.sleep(1.0)
            return SimpleNamespace(text='{"questions": []}', usage_metadata=None)

    models = Models()
    generator = GeminiGenerator("unused", "a", 0.2, client=SimpleNamespace(models=models), fallback_models=("b",))
    started = time.monotonic()
    assert generator.generate(REQUEST).model == "b"
    assert models.calls == ["a", "b"] and time.monotonic() - started < 0.2 * 2 + 0.15


def test_when_every_model_times_out_the_request_still_ends_within_the_overall_limit():
    generator, models = slow_gemini(delay=1.0, timeout=0.2)
    generator.models = ["a", "b", "c"]
    started = time.monotonic()
    with pytest.raises(GenerationError) as info:
        generator.generate(REQUEST)
    assert info.value.kind == "timeout" and info.value.retryable
    assert models.started == 3 and time.monotonic() - started < 0.2 * 3 + 0.15
