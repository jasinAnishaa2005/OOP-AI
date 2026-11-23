"""Fixed-window rate limits stored in the database, so every API worker and server shares the same counters."""

import hashlib
import random
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import get_settings, parse_limit
from app.db import SessionLocal
from app.models import RateLimitBucket


def client_ip(request: Request) -> str:
    # Behind a reverse proxy, run uvicorn with --proxy-headers --forwarded-allow-ips=<proxy IP> so this is the client.
    return request.client.host if request.client else "unknown"


@dataclass(frozen=True)
class Bucket:
    """The counter a request was charged to, so a successful login can hand its attempt back."""

    key: str
    window_start: int


class RateLimiter:
    """Counts run on the request's own database session, so a limited request never needs a second connection.

    Each call commits immediately: the count must survive even if the request fails afterwards."""

    def _charge(self, db: Session, scope: str, subject: str, limit: str) -> tuple[Bucket, int | None]:
        amount, period = parse_limit(limit)
        now = int(time.time())
        window = now - now % period
        key = hashlib.sha256(f"{scope}:{period}:{subject}".encode()).hexdigest()
        insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
        stmt = (
            insert(RateLimitBucket)
            .values(key=key, window_start=window, count=1, expires_at=window + period)
            # A full bucket is left as is: rejected requests never ran, so they must not count as attempts. Otherwise
            # a refund after a correct password could still leave the bucket full and block the next sign-in.
            .on_conflict_do_update(
                index_elements=["key", "window_start"],
                set_={"count": RateLimitBucket.count + 1},
                where=RateLimitBucket.count < amount,
            )
            .returning(RateLimitBucket.count)
        )
        allowed = db.execute(stmt).scalar_one_or_none() is not None
        if random.random() < 0.01:
            self._purge(db, now)
        db.commit()
        return Bucket(key, window), (None if allowed else max(window + period - now, 1))

    def hit(self, db: Session, scope: str, subject: str, limit: str) -> int | None:
        """Count one request; if the limit is already reached, count nothing and return seconds until reset."""
        return self._charge(db, scope, subject, limit)[1]

    def enforce(self, db: Session, scope: str, subject: str, limit: str) -> Bucket | None:
        if not get_settings().rate_limit_enabled:
            return None
        bucket, retry_after = self._charge(db, scope, subject.strip().lower(), limit)
        if retry_after is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many requests. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
        return bucket

    def refund(self, db: Session, bucket: Bucket | None) -> None:
        """Give back an attempt that turned out to be legitimate (e.g. a correct password)."""
        if bucket is None:
            return
        db.execute(
            update(RateLimitBucket)
            .where(
                RateLimitBucket.key == bucket.key,
                RateLimitBucket.window_start == bucket.window_start,
                RateLimitBucket.count > 0,
            )
            .values(count=RateLimitBucket.count - 1)
            .execution_options(synchronize_session=False)
        )
        db.commit()

    @staticmethod
    def _purge(db, now: int) -> None:
        db.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at < now))

    def purge_expired(self) -> None:
        with SessionLocal() as db:
            self._purge(db, int(time.time()))
            db.commit()


limiter = RateLimiter()
