from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class ThesisRevisionModel(Base):
    __tablename__ = "thesis_revisions"
    __table_args__ = (
        CheckConstraint("revision_number > 0", name="ck_thesis_revisions_number"),
        CheckConstraint(
            "status IN ('draft', 'active', 'challenged', 'invalidated', 'archived')",
            name="ck_thesis_revisions_status",
        ),
        CheckConstraint(
            "origin IN ('user_recorded', 'legacy_baseline', 'server_recorded')",
            name="ck_thesis_revisions_origin",
        ),
        UniqueConstraint("thesis_id", "revision_number", name="uq_thesis_revisions_number"),
        Index("ix_thesis_revisions_thesis_created", "thesis_id", "created_at"),
        Index("ix_thesis_revisions_owner_created", "owner_user_id", "created_at"),
        Index("ix_thesis_revisions_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("saved_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_text: Mapped[str] = mapped_column(Text, nullable=False)
    protocols: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assumptions_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    explicit_assumption_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ThesisAssumptionModel(Base):
    """Immutable assumption versions; the companion head row selects the current version."""

    __tablename__ = "thesis_assumptions"
    __table_args__ = (
        CheckConstraint("revision_number > 0", name="ck_thesis_assumptions_number"),
        CheckConstraint(
            "state IN ('active', 'weakened', 'invalidated', 'resolved')",
            name="ck_thesis_assumptions_state",
        ),
        CheckConstraint("origin IN ('user_recorded', 'server_recorded')", name="ck_thesis_assumptions_origin"),
        UniqueConstraint("thesis_id", "assumption_id", "revision_number", name="uq_thesis_assumptions_version"),
        Index("ix_thesis_assumptions_thesis_created", "thesis_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("saved_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    assumption_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_references: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    supersedes_record_id: Mapped[str | None] = mapped_column(ForeignKey("thesis_assumptions.id", ondelete="SET NULL"), nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="user_recorded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ThesisAssumptionHeadModel(Base):
    """Lockable, non-content head for an immutable assumption stream."""

    __tablename__ = "thesis_assumption_heads"
    __table_args__ = (
        UniqueConstraint("thesis_id", "assumption_id", name="uq_thesis_assumption_heads_identity"),
        Index("ix_thesis_assumption_heads_thesis", "thesis_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("saved_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    assumption_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_record_id: Mapped[str] = mapped_column(ForeignKey("thesis_assumptions.id", ondelete="CASCADE"), nullable=False)
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ThesisCatalystModel(Base):
    __tablename__ = "thesis_catalysts"
    __table_args__ = (
        CheckConstraint("revision_number > 0", name="ck_thesis_catalysts_number"),
        CheckConstraint(
            "date_precision IN ('exact', 'month', 'window', 'unknown')",
            name="ck_thesis_catalysts_date_precision",
        ),
        CheckConstraint(
            "status IN ('upcoming', 'occurred', 'missed', 'cancelled', 'unknown')",
            name="ck_thesis_catalysts_status",
        ),
        Index("ix_thesis_catalysts_thesis_date", "thesis_id", "expected_date"),
        Index("ix_thesis_catalysts_owner_created", "owner_user_id", "created_at"),
        Index("ix_thesis_catalysts_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(ForeignKey("saved_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_precision: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="upcoming")
    uncertainty: Mapped[str | None] = mapped_column(String(512), nullable=True)
    evidence_references: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ResearchReportComparisonModel(Base):
    __tablename__ = "research_report_comparisons"
    __table_args__ = (
        CheckConstraint("scope_class IN ('private', 'organization')", name="ck_research_report_comparisons_scope"),
        CheckConstraint("schema_version = 'research_comparison.v1'", name="ck_research_report_comparisons_schema"),
        UniqueConstraint("left_report_id", "right_report_id", "scope_key", name="uq_research_report_comparisons_inputs"),
        Index("ix_research_report_comparisons_owner_created", "owner_user_id", "created_at"),
        Index("ix_research_report_comparisons_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    left_report_id: Mapped[str] = mapped_column(String(64), nullable=False)
    right_report_id: Mapped[str] = mapped_column(String(64), nullable=False)
    left_input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    right_input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_class: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="research_comparison.v1")
    comparison_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    lineage_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
