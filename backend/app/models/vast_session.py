from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class VastSessionModel(Base):
    __tablename__ = "vast_sessions"
    __table_args__ = (
        UniqueConstraint("source_job_id", name="uq_vast_sessions_source_job"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="vast_ai", nullable=False)
    source_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vast_instance_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    vast_contract_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    offer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    image: Mapped[str] = mapped_column(String(512), nullable=False)
    gpu_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hourly_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_runtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    container_port: Mapped[int] = mapped_column(Integer, nullable=False)
    public_endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    health_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleanup_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
