from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class WatchlistItemModel(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        Index("ix_watchlist_items_owner_deleted", "owner_user_id", "deleted_at"),
        Index(
            "ix_watchlist_items_org_visibility_deleted",
            "organization_id",
            "visibility",
            "deleted_at",
        ),
        Index("ix_watchlist_items_anonymous_expires", "anonymous_session_id", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    market_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
