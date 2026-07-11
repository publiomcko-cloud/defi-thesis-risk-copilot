from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class EvaluationResultModel(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discovered_item_id: Mapped[str] = mapped_column(
        ForeignKey("discovered_items.id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_rating: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_summary: Mapped[str] = mapped_column(Text, nullable=False)
    missing_data_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sources_json: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
