from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class DiscoveredItemModel(Base):
    __tablename__ = "discovered_items"
    __table_args__ = (
        UniqueConstraint("discovery_key", name="uq_discovered_items_discovery_key"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discovery_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="needs_review", nullable=False)
