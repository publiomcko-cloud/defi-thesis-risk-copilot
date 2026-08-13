from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class PrivacyPreferenceDecisionModel(Base):
    __tablename__ = "privacy_preference_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('grant', 'deny', 'withdraw')",
            name="ck_privacy_preference_decisions_decision",
        ),
        CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_privacy_preference_decisions_purpose",
        ),
        CheckConstraint(
            "source IN ('account_ui')",
            name="ck_privacy_preference_decisions_source",
        ),
        UniqueConstraint(
            "user_id",
            "purpose",
            "idempotency_key",
            name="uq_privacy_preference_decisions_idempotency",
        ),
        Index(
            "ix_privacy_preference_decisions_user_purpose_occurred",
            "user_id",
            "purpose",
            "occurred_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("privacy_preference_decisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class PrivacyPreferenceModel(Base):
    __tablename__ = "privacy_preferences"
    __table_args__ = (
        CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_privacy_preferences_purpose",
        ),
        UniqueConstraint("user_id", "purpose", name="uq_privacy_preferences_user_purpose"),
        Index("ix_privacy_preferences_user_enabled", "user_id", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    latest_decision_id: Mapped[str] = mapped_column(
        ForeignKey("privacy_preference_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ProductAnalyticsEventModel(Base):
    __tablename__ = "product_analytics_events"
    __table_args__ = (
        CheckConstraint(
            "event_name IN ('analysis_completed', 'analysis_failed', 'thesis_saved', 'watchlist_created')",
            name="ck_product_analytics_events_name",
        ),
        CheckConstraint(
            "purpose = 'product_improvement'",
            name="ck_product_analytics_events_purpose",
        ),
        CheckConstraint(
            "actor_class IN ('authenticated', 'organization_context')",
            name="ck_product_analytics_events_actor_class",
        ),
        CheckConstraint("schema_version > 0", name="ck_product_analytics_events_schema_version"),
        UniqueConstraint("event_key", name="uq_product_analytics_events_event_key"),
        Index("ix_product_analytics_events_name_occurred", "event_name", "occurred_at"),
        Index("ix_product_analytics_events_owner_occurred", "owner_user_id", "occurred_at"),
        Index("ix_product_analytics_events_expiry", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_class: Mapped[str] = mapped_column(String(32), nullable=False)
    dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    event_key: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("privacy_preference_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _reject_immutable_update(_mapper, _connection, _target) -> None:
    raise ValueError("Phase 20B decision and analytics event rows are append-only")


event.listen(PrivacyPreferenceDecisionModel, "before_update", _reject_immutable_update)
event.listen(ProductAnalyticsEventModel, "before_update", _reject_immutable_update)
