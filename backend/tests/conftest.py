import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256-signing")
os.environ.setdefault("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///./test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import limiter  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.email import get_email_sender  # noqa: E402


class OutboxSender:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.messages.append({"to": to, "subject": subject, "body": body})


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def outbox() -> OutboxSender:
    sender = OutboxSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield sender
    app.dependency_overrides.pop(get_email_sender, None)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


VALID_USER = {
    "full_name": "Ada Lovelace",
    "email": "Ada@Example.com",
    "student_id": "CSE-2024-001",
    "password": "objects4ever",
}


@pytest.fixture
def registered(client: TestClient) -> dict:
    res = client.post("/api/auth/register", json=VALID_USER)
    assert res.status_code == 201, res.text
    return res.json()
