from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanVersionModel(Base):
    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("plan_key", "version", name="uq_plan_versions_key_version"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class PlanEntitlementModel(Base):
    __tablename__ = "plan_entitlements"
    __table_args__ = (UniqueConstraint("plan_version_id", "entitlement_key", name="uq_plan_entitlements_version_key"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("plan_versions.id", ondelete="RESTRICT"), nullable=False)
    entitlement_key: Mapped[str] = mapped_column(String(96), nullable=False)
    hard_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class EntitlementAssignmentModel(Base):
    __tablename__ = "entitlement_assignments"
    __table_args__ = (
        CheckConstraint("subject_type = 'user'", name="ck_entitlement_assignments_user_only"),
        UniqueConstraint("subject_type", "subject_id", "plan_version_id", "effective_from", name="uq_entitlement_assignment_identity"),
        Index("ix_entitlement_assignments_resolver", "subject_type", "subject_id", "effective_from", "effective_until"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    subject_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_version_id: Mapped[str] = mapped_column(ForeignKey("plan_versions.id", ondelete="RESTRICT"), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="server_default")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class UsageEventModel(Base):
    __tablename__ = "non_billable_usage_events"
    __table_args__ = (
        CheckConstraint("unit_key IN ('usage.analysis.completed.v1', 'usage.simulation.completed.v1', 'usage.options.completed.v1', 'usage.schedule.run_completed.v1')", name="ck_non_billable_usage_unit_key"),
        UniqueConstraint("unit_key", "logical_key", name="uq_non_billable_usage_unit_logical"),
        UniqueConstraint("reverses_event_id", name="uq_non_billable_usage_reversal"),
        Index("ix_non_billable_usage_subject_unit", "owner_user_id", "unit_key", "occurred_at"),
        Index("ix_non_billable_usage_source", "source_type", "source_id"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    unit_key: Mapped[str] = mapped_column(String(96), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    logical_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reverses_event_id: Mapped[str | None] = mapped_column(ForeignKey("non_billable_usage_events.id", ondelete="RESTRICT"))
    correction_code: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
