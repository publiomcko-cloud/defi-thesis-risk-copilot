from datetime import UTC, datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'leased', 'running', 'retry_wait', 'completed', 'failed', "
            "'cancel_requested', 'cancelled', 'dead_letter')",
            name="ck_jobs_status",
        ),
        CheckConstraint("priority_class IN ('standard', 'elevated', 'admin')", name="ck_jobs_priority_class"),
        CheckConstraint("visibility IN ('private', 'organization')", name="ck_jobs_visibility"),
        CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count"),
        CheckConstraint("max_attempts > 0", name="ck_jobs_max_attempts"),
        CheckConstraint("lease_generation >= 0", name="ck_jobs_lease_generation"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_jobs_progress_percent"),
        CheckConstraint("estimated_cost_microusd >= 0", name="ck_jobs_estimated_cost"),
        CheckConstraint("reserved_cost_microusd >= 0", name="ck_jobs_reserved_cost"),
        CheckConstraint("actual_cost_microusd >= 0", name="ck_jobs_actual_cost"),
        UniqueConstraint(
            "idempotency_subject_type",
            "idempotency_subject_id",
            "job_type",
            "idempotency_key",
            name="uq_jobs_idempotency_scope",
        ),
        Index("ix_jobs_claim", "status", "priority_class", "available_at", "created_at"),
        Index("ix_jobs_owner_status", "owner_user_id", "status", "available_at"),
        Index("ix_jobs_org_status", "organization_id", "status", "available_at"),
        Index("ix_jobs_retention", "deleted_at", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    priority_class: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False, index=True)
    input_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    result_schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    queue_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leased_by_worker_id: Mapped[str | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lease_generation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    idempotency_subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_cost_microusd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reserved_cost_microusd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    actual_cost_microusd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    replay_of_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobAttemptModel(Base):
    __tablename__ = "job_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="ck_job_attempts_number"),
        CheckConstraint("lease_generation > 0", name="ck_job_attempts_generation"),
        CheckConstraint("runtime_ms >= 0", name="ck_job_attempts_runtime"),
        CheckConstraint("estimated_cost_microusd >= 0", name="ck_job_attempts_estimated_cost"),
        CheckConstraint("actual_cost_microusd >= 0", name="ck_job_attempts_actual_cost"),
        UniqueConstraint("job_id", "attempt_number", name="uq_job_attempts_number"),
        UniqueConstraint("job_id", "lease_generation", name="uq_job_attempts_generation"),
        Index("ix_job_attempts_worker_outcome", "worker_id", "outcome", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lease_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    estimated_cost_microusd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    actual_cost_microusd: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class JobEventModel(Base):
    __tablename__ = "job_events"
    __table_args__ = (
        UniqueConstraint("job_id", "sequence_number", name="uq_job_events_sequence"),
        Index("ix_job_events_job_created", "job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    worker_id: Mapped[str | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
