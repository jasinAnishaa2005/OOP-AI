import re
from datetime import timedelta

from sqlalchemy import select

from app.core.time import utcnow
from app.db import SessionLocal
from app.models import PasswordResetToken, User
from tests.conftest import VALID_USER


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_returns_tokens_and_normalized_user(registered):
    assert registered["token_type"] == "bearer"
    assert registered["access_token"] and registered["refresh_token"]
    assert registered["user"]["email"] == "ada@example.com"
    assert registered["user"]["role"] == "student"
    assert "password" not in str(registered["user"]).lower()


def test_password_is_hashed(registered):
    with SessionLocal() as db:
        user = db.scalars(select(User)).one()
    assert user.password_hash != VALID_USER["password"]
    assert user.password_hash.startswith("$argon2")


def test_register_duplicate_email_and_student_id(client, registered):
    res = client.post("/api/auth/register", json={**VALID_USER, "student_id": "OTHER-1"})
    assert res.status_code == 409 and "email" in res.json()["detail"]
    res = client.post("/api/auth/register", json={**VALID_USER, "email": "new@example.com"})
    assert res.status_code == 409 and "student ID" in res.json()["detail"]


def test_register_validation(client):
    weak = client.post("/api/auth/register", json={**VALID_USER, "password": "onlyletters"})
    assert weak.status_code == 422
    short = client.post("/api/auth/register", json={**VALID_USER, "password": "a1"})
    assert short.status_code == 422
    bad_email = client.post("/api/auth/register", json={**VALID_USER, "email": "not-an-email"})
    assert bad_email.status_code == 422
    bad_id = client.post("/api/auth/register", json={**VALID_USER, "student_id": "x'; DROP TABLE users;--"})
    assert bad_id.status_code == 422


def test_register_without_student_id(client):
    res = client.post("/api/auth/register", json={**VALID_USER, "student_id": ""})
    assert res.status_code == 201
    assert res.json()["user"]["student_id"] is None


def test_login_with_email_or_student_id(client, registered):
    by_email = client.post(
        "/api/auth/login", json={"identifier": "ADA@example.com", "password": VALID_USER["password"]}
    )
    assert by_email.status_code == 200
    by_id = client.post("/api/auth/login", json={"identifier": "CSE-2024-001", "password": VALID_USER["password"]})
    assert by_id.status_code == 200


def test_login_rejects_bad_credentials_generically(client, registered):
    wrong_pw = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "wrong-pass1"})
    unknown = client.post("/api/auth/login", json={"identifier": "nobody@example.com", "password": "wrong-pass1"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_login_disabled_account(client, registered):
    with SessionLocal() as db:
        user = db.scalars(select(User)).one()
        user.is_active = False
        db.commit()
    res = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": VALID_USER["password"]})
    assert res.status_code == 403


def test_me_requires_valid_token(client, registered):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth_header("garbage")).status_code == 401
    res = client.get("/api/auth/me", headers=auth_header(registered["access_token"]))
    assert res.status_code == 200 and res.json()["email"] == "ada@example.com"


def test_refresh_token_cannot_be_used_as_access_token(client, registered):
    assert client.get("/api/auth/me", headers=auth_header(registered["refresh_token"])).status_code == 401


def test_refresh_rotates_and_detects_reuse(client, registered):
    first = registered["refresh_token"]
    res = client.post("/api/auth/refresh", json={"refresh_token": first})
    assert res.status_code == 200
    second = res.json()["refresh_token"]
    assert second != first
    # Reusing the rotated token fails and revokes the whole session family.
    assert client.post("/api/auth/refresh", json={"refresh_token": first}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": second}).status_code == 401


def test_logout_revokes_access_and_refresh(client, registered):
    headers = auth_header(registered["access_token"])
    res = client.post("/api/auth/logout", json={"refresh_token": registered["refresh_token"]}, headers=headers)
    assert res.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": registered["refresh_token"]}).status_code == 401


def test_logout_requires_auth(client):
    assert client.post("/api/auth/logout").status_code == 401


def _reset_token_from(outbox) -> str:
    match = re.search(r"Reset code: (\S+)", outbox.messages[-1]["body"])
    assert match
    return match.group(1)


def test_forgot_password_does_not_reveal_accounts(client, registered, outbox):
    known = client.post("/api/auth/forgot-password", json={"email": "ada@example.com"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox.messages) == 1 and outbox.messages[0]["to"] == "ada@example.com"


def test_reset_password_flow(client, registered, outbox):
    client.post("/api/auth/forgot-password", json={"email": "ada@example.com"})
    token = _reset_token_from(outbox)
    res = client.post("/api/auth/reset-password", json={"token": token, "new_password": "newSecret99"})
    assert res.status_code == 200
    # Token is single use; old password and old sessions no longer work.
    assert (
        client.post("/api/auth/reset-password", json={"token": token, "new_password": "another1x"}).status_code == 400
    )
    old = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": VALID_USER["password"]})
    assert old.status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": registered["refresh_token"]}).status_code == 401
    new = client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "newSecret99"})
    assert new.status_code == 200


def test_reset_password_rejects_expired_token(client, registered, outbox):
    client.post("/api/auth/forgot-password", json={"email": "ada@example.com"})
    token = _reset_token_from(outbox)
    with SessionLocal() as db:
        record = db.scalars(select(PasswordResetToken)).one()
        record.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    res = client.post("/api/auth/reset-password", json={"token": token, "new_password": "newSecret99"})
    assert res.status_code == 400


def test_login_is_rate_limited(client, registered):
    statuses = [
        client.post("/api/auth/login", json={"identifier": "ada@example.com", "password": "wrong-pass1"}).status_code
        for _ in range(12)
    ]
    assert statuses[-1] == 429
