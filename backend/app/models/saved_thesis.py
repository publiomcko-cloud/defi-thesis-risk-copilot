from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class SavedThesisModel(Base):
    __tablename__ = "saved_theses"
    __table_args__ = (
        Index("ix_saved_theses_owner_deleted", "owner_user_id", "deleted_at"),
        Index("ix_saved_theses_org_visibility_deleted", "organization_id", "visibility", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_text: Mapped[str] = mapped_column(Text, nullable=False)
    protocols: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assumptions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
