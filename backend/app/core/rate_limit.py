"""Fixed-window rate limits stored in the database, so every API worker and server shares the same counters."""

import hashlib
import random
import time

from fastapi import HTTPException, Request, status
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import get_settings, parse_limit
from app.db import SessionLocal
from app.models import RateLimitBucket


def client_ip(request: Request) -> str:
    # Behind a reverse proxy, run uvicorn with --proxy-headers --forwarded-allow-ips=<proxy IP> so this is the client.
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def hit(self, scope: str, subject: str, limit: str) -> int | None:
        """Count one request; returns seconds until the window resets if the limit is exceeded, else None."""
        amount, period = parse_limit(limit)
        now = int(time.time())
        window = now - now % period
        key = hashlib.sha256(f"{scope}:{period}:{subject}".encode()).hexdigest()
        with SessionLocal() as db:
            insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
            stmt = (
                insert(RateLimitBucket)
                .values(key=key, window_start=window, count=1, expires_at=window + period)
                .on_conflict_do_update(
                    index_elements=["key", "window_start"], set_={"count": RateLimitBucket.count + 1}
                )
                .returning(RateLimitBucket.count)
            )
            count = db.execute(stmt).scalar_one()
            if random.random() < 0.01:
                self._purge(db, now)
            db.commit()
        return max(window + period - now, 1) if count > amount else None

    def enforce(self, scope: str, subject: str, limit: str) -> None:
        if not get_settings().rate_limit_enabled:
            return
        retry_after = self.hit(scope, subject.strip().lower(), limit)
        if retry_after is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many requests. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    @staticmethod
    def _purge(db, now: int) -> None:
        db.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at < now))

    def purge_expired(self) -> None:
        with SessionLocal() as db:
            self._purge(db, int(time.time()))
            db.commit()


limiter = RateLimiter()
