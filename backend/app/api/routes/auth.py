from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import AuthContext, get_current_user, get_optional_auth_context
from app.core.rate_limit import client_ip, limiter
from app.db import get_db
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth as auth_service
from app.services.email import EmailSender, get_email_sender

router = APIRouter(prefix="/auth", tags=["auth"])


def _limit(db: Session, request: Request, scope: str, identifier: str | None = None) -> None:
    """A generous per-IP limit (campus NAT) plus a strict per-identifier limit."""
    settings = get_settings()
    limiter.enforce(db, f"auth:{scope}:ip", client_ip(request), settings.auth_ip_rate_limit)
    if identifier:
        limiter.enforce(db, f"auth:{scope}:account", identifier, settings.auth_rate_limit)


def _tokens_response(tokens: auth_service.IssuedTokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(tokens.user),
    )


def _raise(exc: auth_service.AuthError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _limit(db, request, "register", body.email)
    try:
        user = auth_service.register_user(db, body)
    except auth_service.AuthError as exc:
        _raise(exc)
    return _tokens_response(auth_service.issue_tokens(db, user))


@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    ip = client_ip(request)
    limiter.enforce(db, "auth:login:ip", ip, settings.auth_ip_rate_limit)
    account = auth_service.find_login_user(db, body.identifier)
    subject = auth_service.login_subject(account, body.identifier)
    # Failed guesses are capped per account from one network, and more loosely per account from everywhere,
    # so a stranger cannot lock a student out by spending a single shared budget.
    charged = [
        limiter.enforce(db, "auth:login:account-ip", f"{subject}|{ip}", settings.auth_rate_limit),
        limiter.enforce(db, "auth:login:account", subject, settings.auth_account_rate_limit),
    ]
    try:
        user = auth_service.authenticate(db, body.identifier, body.password, account)
    except auth_service.AuthError as exc:
        _raise(exc)
    for bucket in charged:  # a correct password is not a guess
        limiter.refund(db, bucket)
    return _tokens_response(auth_service.issue_tokens(db, user, remember_me=body.remember_me))


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _limit(db, request, "refresh")
    try:
        tokens = auth_service.rotate_refresh_token(db, body.refresh_token)
    except auth_service.AuthError as exc:
        _raise(exc)
    return _tokens_response(tokens)


@router.post("/logout", response_model=MessageResponse)
def logout(
    body: LogoutRequest | None = None,
    ctx: AuthContext | None = Depends(get_optional_auth_context),
    db: Session = Depends(get_db),
) -> MessageResponse:
    # The refresh token alone is enough, so signing out still works after the access token expired.
    refresh_token = body.refresh_token if body else None
    if ctx is None and not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"}
        )
    auth_service.logout(db, ctx.token_payload if ctx else None, refresh_token)
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
) -> MessageResponse:
    _limit(db, request, "forgot-password", body.email)
    auth_service.request_password_reset(db, body.email, sender)
    return MessageResponse(message="If an account exists for this email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    _limit(db, request, "reset-password")
    try:
        auth_service.reset_password(db, body.token, body.new_password)
    except auth_service.AuthError as exc:
        _raise(exc)
    return MessageResponse(message="Password updated. Please sign in with your new password.")
