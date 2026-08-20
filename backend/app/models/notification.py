from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class NotificationPreferenceModel(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        CheckConstraint("quiet_hours_start IS NULL OR (length(quiet_hours_start) = 5 AND substr(quiet_hours_start, 3, 1) = ':' AND quiet_hours_start >= '00:00' AND quiet_hours_start <= '23:59')", name="ck_notification_preferences_quiet_start"),
        CheckConstraint("quiet_hours_end IS NULL OR (length(quiet_hours_end) = 5 AND substr(quiet_hours_end, 3, 1) = ':' AND quiet_hours_end >= '00:00' AND quiet_hours_end <= '23:59')", name="ck_notification_preferences_quiet_end"),
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_enabled_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    minimum_severity_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    daily_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "category IN ('monitoring.risk_alert', 'schedule.status', 'job.status', 'account.lifecycle')",
            name="ck_notifications_category",
        ),
        CheckConstraint(
            "severity IN ('informational', 'warning', 'critical')",
            name="ck_notifications_severity",
        ),
        CheckConstraint(
            "policy_outcome IN ('available', 'delayed_quiet_hours', 'delayed_digest', 'suppressed_by_preference', 'mandatory')",
            name="ck_notifications_policy_outcome",
        ),
        UniqueConstraint("owner_user_id", "idempotency_key", name="uq_notifications_owner_idempotency"),
        Index("ix_notifications_owner_available", "owner_user_id", "available_at", "created_at"),
        Index("ix_notifications_owner_unread", "owner_user_id", "read_at", "available_at"),
        Index("ix_notifications_retention", "expires_at"),
        Index("ix_notifications_source", "source_type", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    template_id: Mapped[str] = mapped_column(String(96), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    navigation_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    policy_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
