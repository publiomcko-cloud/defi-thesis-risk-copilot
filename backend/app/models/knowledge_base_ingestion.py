from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeBaseIngestionModel(Base):
    __tablename__ = "knowledge_base_ingestions"
    __table_args__ = (
        UniqueConstraint("review_item_id", name="uq_knowledge_base_ingestions_review_item_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generated_markdown_path: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    ingested_by: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ingested", nullable=False)
