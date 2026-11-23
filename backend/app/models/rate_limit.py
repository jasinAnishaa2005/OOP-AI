from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RateLimitBucket(Base):
    """Fixed-window request counter shared by every API worker. `key` is a hash, never a raw IP or email."""

    __tablename__ = "rate_limit_buckets"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
