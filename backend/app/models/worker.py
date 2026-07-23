from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class WorkerModel(Base):
    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled', 'stale', 'revoked')", name="ck_workers_status"),
        CheckConstraint("max_concurrency > 0", name="ck_workers_max_concurrency"),
        UniqueConstraint("name", name="uq_workers_name"),
        Index("ix_workers_status_last_seen", "status", "last_seen_at"),
        Index("ix_workers_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    protocol_version: Mapped[str] = mapped_column(String(32), nullable=False)
    software_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    allowed_job_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class WorkerCredentialModel(Base):
    __tablename__ = "worker_credentials"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'revoked', 'expired')", name="ck_worker_credentials_status"),
        UniqueConstraint("token_prefix", name="uq_worker_credentials_prefix"),
        UniqueConstraint("token_hash", name="uq_worker_credentials_hash"),
        Index("ix_worker_credentials_worker_status", "worker_id", "status", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    token_prefix: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    allowed_job_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("worker_credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
