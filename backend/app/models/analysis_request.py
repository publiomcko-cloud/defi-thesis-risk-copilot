from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class AnalysisRequestModel(Base):
    __tablename__ = "analysis_requests"
    __table_args__ = (
        Index("ix_analysis_requests_owner_deleted", "owner_user_id", "deleted_at"),
        Index(
            "ix_analysis_requests_org_visibility_deleted",
            "organization_id",
            "visibility",
            "deleted_at",
        ),
        Index("ix_analysis_requests_anonymous_expires", "anonymous_session_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_description: Mapped[str] = mapped_column(Text, nullable=False)
    protocols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    market_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_inputs_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_depth: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False, index=True)
    anonymous_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("anonymous_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reports = relationship("ReportModel", back_populates="analysis_request")
