from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonitoringScheduleModel(Base):
    """A user-owned, code-targeted durable monitoring schedule."""

    __tablename__ = "monitoring_schedules"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'deleted')", name="ck_monitoring_schedules_status"),
        CheckConstraint("target_type = 'watchlist.evaluate'", name="ck_monitoring_schedules_target_type"),
        CheckConstraint("cadence IN ('hourly', 'six_hourly', 'daily', 'weekly')", name="ck_monitoring_schedules_cadence"),
        Index("ix_monitoring_schedules_due", "status", "next_due_at", "deleted_at"),
        Index("ix_monitoring_schedules_owner_status", "owner_user_id", "status", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cadence: Mapped[str] = mapped_column(String(32), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MonitoringScheduleOccurrenceModel(Base):
    """One immutable scheduled execution identity and its controlled job linkage."""

    __tablename__ = "monitoring_schedule_occurrences"
    __table_args__ = (
        CheckConstraint(
            "status IN ('claimed', 'queued', 'running', 'completed', 'failed', 'denied', 'missed', 'cancel_requested', 'cancelled')",
            name="ck_monitoring_schedule_occurrences_status",
        ),
        UniqueConstraint("schedule_id", "scheduled_for", name="uq_monitoring_schedule_occurrence_time"),
        Index("ix_monitoring_schedule_occurrences_schedule_time", "schedule_id", "scheduled_for"),
        Index("ix_monitoring_schedule_occurrences_expiry", "expires_at"),
        Index("ix_monitoring_schedule_occurrences_job", "job_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(
        ForeignKey("monitoring_schedules.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
