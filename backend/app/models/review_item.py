from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewItemModel(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("discovered_item_id", name="uq_review_items_discovered_item_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discovered_item_id: Mapped[str] = mapped_column(
        ForeignKey("discovered_items.id"),
        nullable=False,
        index=True,
    )
    evaluation_result_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_results.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="needs_review", nullable=False)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_for_rag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
