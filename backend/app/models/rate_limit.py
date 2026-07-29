from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RateLimitBucketModel(Base):
    """A shared, privacy-preserving fixed-window rate-limit counter."""

    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('ip', 'session', 'user', 'organization')",
            name="ck_rate_limit_buckets_scope_type",
        ),
        CheckConstraint("window_seconds > 0", name="ck_rate_limit_buckets_window_seconds"),
        CheckConstraint("request_count >= 0", name="ck_rate_limit_buckets_request_count"),
        CheckConstraint("limit_value > 0", name="ck_rate_limit_buckets_limit_value"),
        UniqueConstraint(
            "scope_type",
            "scope_key_hash",
            "action",
            "window_seconds",
            "window_started_at",
            name="uq_rate_limit_buckets_scope_window",
        ),
        Index("ix_rate_limit_buckets_expiry", "expires_at"),
        Index("ix_rate_limit_buckets_action_expiry", "action", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # This is an HMAC-derived value. Raw IP addresses, session IDs, user IDs,
    # and organization IDs are intentionally never persisted in this table.
    scope_key_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
