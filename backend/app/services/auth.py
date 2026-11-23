import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.core.time import as_utc, utcnow
from app.models import PasswordResetToken, RefreshToken, RevokedAccessToken, User
from app.schemas.auth import RegisterRequest
from app.services.email import EmailSender

# Verifying against a real hash keeps login timing similar for unknown accounts.
logger = logging.getLogger(__name__)

_DUMMY_HASH = hash_password("timing-equalizer-password-1")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


def register_user(db: Session, data: RegisterRequest) -> User:
    conditions = [User.email == data.email]
    if data.student_id:
        conditions.append(User.student_id == data.student_id)
    existing = db.scalars(select(User).where(or_(*conditions))).first()
    if existing:
        field = "email" if existing.email == data.email else "student ID"
        raise AuthError(f"An account with this {field} already exists", status_code=409)

    user = User(
        email=data.email,
        student_id=data.student_id,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent registration won the race for the same email or student ID.
        db.rollback()
        raise AuthError("An account with this email or student ID already exists", status_code=409) from None
    db.refresh(user)
    return user


def find_login_user(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip()
    return db.scalars(select(User).where(or_(User.email == identifier.lower(), User.student_id == identifier))).first()


def login_subject(user: User | None, identifier: str) -> str:
    """One rate-limit identity per account, whichever of its identifiers (email or student ID) is typed."""
    return f"user:{user.id}" if user else f"unknown:{identifier.strip().lower()}"


def authenticate(db: Session, identifier: str, password: str, user: User | None = None) -> User:
    user = user or find_login_user(db, identifier)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise AuthError("Invalid credentials", status_code=401)
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid credentials", status_code=401)
    if not user.is_active:
        raise AuthError("This account is disabled", status_code=403)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def issue_tokens(db: Session, user: User, remember_me: bool = False) -> IssuedTokens:
    settings = get_settings()
    access_token, access_expires = create_access_token(user.id)
    refresh_token = generate_opaque_token()
    days = settings.remember_me_refresh_token_days if remember_me else settings.refresh_token_days
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_opaque_token(refresh_token),
            expires_at=utcnow() + timedelta(days=days),
        )
    )
    db.commit()
    return IssuedTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int((access_expires - utcnow()).total_seconds()),
        user=user,
    )


def rotate_refresh_token(db: Session, refresh_token: str) -> IssuedTokens:
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(refresh_token))).first()
    now = utcnow()
    if record is None or record.revoked_at is not None or as_utc(record.expires_at) <= now:
        if record is not None and record.revoked_at is not None:
            # Reuse of a rotated token: revoke every session of this user.
            _revoke_all_refresh_tokens(db, record.user_id)
            db.commit()
        raise AuthError("Invalid or expired refresh token", status_code=401)
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthError("Invalid or expired refresh token", status_code=401)

    remaining = as_utc(record.expires_at) - now
    # Conditional update so concurrent requests cannot both consume the same token.
    claimed = db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == record.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    if claimed.rowcount != 1:
        db.rollback()
        _revoke_all_refresh_tokens(db, user.id)
        db.commit()
        raise AuthError("Invalid or expired refresh token", status_code=401)
    access_token, access_expires = create_access_token(user.id)
    new_refresh = generate_opaque_token()
    db.add(RefreshToken(user_id=user.id, token_hash=hash_opaque_token(new_refresh), expires_at=now + remaining))
    db.commit()
    return IssuedTokens(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=int((access_expires - now).total_seconds()),
        user=user,
    )


def logout(db: Session, access_payload: dict | None, refresh_token: str | None) -> None:
    if access_payload:
        db.merge(
            RevokedAccessToken(
                jti=access_payload["jti"],
                expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc),
            )
        )
    if refresh_token:
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_opaque_token(refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=utcnow())
        )
    db.execute(delete(RevokedAccessToken).where(RevokedAccessToken.expires_at < utcnow()))
    db.commit()


def is_access_token_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedAccessToken, jti) is not None


def request_password_reset(db: Session, email: str, sender: EmailSender) -> None:
    settings = get_settings()
    user = db.scalars(select(User).where(User.email == email.lower())).first()
    if user is None or not user.is_active:
        return
    token = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(token),
            expires_at=utcnow() + timedelta(minutes=settings.password_reset_minutes),
        )
    )
    db.commit()
    link = f"{settings.password_reset_url}?token={token}"
    try:
        _send_reset_email(sender, user, link, token)
    except Exception:
        # Same response as for unknown emails, so delivery failures do not reveal registered accounts.
        logger.exception("Failed to send password reset email")


def _send_reset_email(sender: EmailSender, user: User, link: str, token: str) -> None:
    settings = get_settings()
    sender.send(
        to=user.email,
        subject="Reset your OOP-AI password",
        body=(
            f"Hi {user.full_name},\n\n"
            f"Use this link to reset your OOP-AI password. It expires in {settings.password_reset_minutes} minutes.\n\n"
            f"{link}\n\nReset code: {token}\n\n"
            "If you did not request this, you can ignore this email."
        ),
    )


def reset_password(db: Session, token: str, new_password: str) -> None:
    record = db.scalars(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_opaque_token(token))
    ).first()
    now = utcnow()
    if record is None or record.used_at is not None or as_utc(record.expires_at) <= now:
        raise AuthError("Invalid or expired reset token", status_code=400)
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthError("Invalid or expired reset token", status_code=400)
    claimed = db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.id == record.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise AuthError("Invalid or expired reset token", status_code=400)
    user.password_hash = hash_password(new_password)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    _revoke_all_refresh_tokens(db, user.id)
    db.commit()


def _revoke_all_refresh_tokens(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
