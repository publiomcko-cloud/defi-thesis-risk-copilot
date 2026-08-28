from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerRequestModel(Base):
    """Private, owner-scoped first-party support and privacy intake."""

    __tablename__ = "customer_requests"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('support', 'feedback', 'abuse_report', 'privacy_access_export', 'privacy_deletion')",
            name="ck_customer_requests_request_type",
        ),
        CheckConstraint(
            "workflow_state IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_customer_requests_workflow_state",
        ),
        CheckConstraint(
            "verification_state IN ('not_required', 'authenticated')",
            name="ck_customer_requests_verification_state",
        ),
        CheckConstraint("length(subject) >= 1 AND length(subject) <= 120", name="ck_customer_requests_subject_length"),
        CheckConstraint(
            "length(description) >= 1 AND length(description) <= 4000",
            name="ck_customer_requests_description_length",
        ),
        CheckConstraint(
            "resolution_code IS NULL OR (length(resolution_code) >= 1 AND length(resolution_code) <= 64)",
            name="ck_customer_requests_resolution_code_length",
        ),
        Index("ix_customer_requests_owner_created", "owner_user_id", "created_at"),
        Index("ix_customer_requests_organization", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    workflow_state: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    verification_state: Mapped[str] = mapped_column(String(16), nullable=False)
    resolution_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
