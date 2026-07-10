from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class AnalysisRequestModel(Base):
    __tablename__ = "analysis_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_description: Mapped[str] = mapped_column(Text, nullable=False)
    protocols: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    market_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_inputs_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_depth: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    reports = relationship("ReportModel", back_populates="analysis_request")
