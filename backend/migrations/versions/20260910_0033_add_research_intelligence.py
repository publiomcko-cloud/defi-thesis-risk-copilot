"""Add source-grounded research intelligence.

Revision ID: 20260910_0033
Revises: 20260907_0032
"""

from alembic import op
import sqlalchemy as sa


revision = "20260910_0033"
down_revision = "20260907_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "thesis_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("thesis_id", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("strategy_text", sa.Text(), nullable=False),
        sa.Column("protocols", sa.JSON(), nullable=False),
        sa.Column("assumptions_snapshot", sa.JSON(), nullable=False),
        sa.Column("explicit_assumption_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("change_reason", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_thesis_revisions_number"),
        sa.CheckConstraint("status IN ('draft', 'active', 'challenged', 'invalidated', 'archived')", name="ck_thesis_revisions_status"),
        sa.CheckConstraint("origin IN ('user_recorded', 'legacy_baseline', 'server_recorded')", name="ck_thesis_revisions_origin"),
        sa.ForeignKeyConstraint(["thesis_id"], ["saved_theses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thesis_id", "revision_number", name="uq_thesis_revisions_number"),
    )
    op.create_index("ix_thesis_revisions_thesis_created", "thesis_revisions", ["thesis_id", "created_at"])
    op.create_index("ix_thesis_revisions_owner_created", "thesis_revisions", ["owner_user_id", "created_at"])
    op.create_index("ix_thesis_revisions_org_created", "thesis_revisions", ["organization_id", "created_at"])

    op.create_table(
        "thesis_assumptions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("thesis_id", sa.String(length=64), nullable=False),
        sa.Column("assumption_id", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("supersedes_record_id", sa.String(length=64), nullable=True),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_thesis_assumptions_number"),
        sa.CheckConstraint("state IN ('active', 'weakened', 'invalidated', 'resolved')", name="ck_thesis_assumptions_state"),
        sa.CheckConstraint("origin IN ('user_recorded', 'server_recorded')", name="ck_thesis_assumptions_origin"),
        sa.ForeignKeyConstraint(["thesis_id"], ["saved_theses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_record_id"], ["thesis_assumptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thesis_id", "assumption_id", "revision_number", name="uq_thesis_assumptions_version"),
    )
    op.create_index("ix_thesis_assumptions_thesis_created", "thesis_assumptions", ["thesis_id", "created_at"])

    op.create_table(
        "thesis_assumption_heads",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("thesis_id", sa.String(length=64), nullable=False),
        sa.Column("assumption_id", sa.String(length=64), nullable=False),
        sa.Column("current_record_id", sa.String(length=64), nullable=False),
        sa.Column("current_revision_number", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["thesis_id"], ["saved_theses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_record_id"], ["thesis_assumptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thesis_id", "assumption_id", name="uq_thesis_assumption_heads_identity"),
    )
    op.create_index("ix_thesis_assumption_heads_thesis", "thesis_assumption_heads", ["thesis_id"])

    op.create_table(
        "thesis_catalysts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("thesis_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("uncertainty", sa.String(length=512), nullable=True),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="ck_thesis_catalysts_number"),
        sa.CheckConstraint("date_precision IN ('exact', 'month', 'window', 'unknown')", name="ck_thesis_catalysts_date_precision"),
        sa.CheckConstraint("status IN ('upcoming', 'occurred', 'missed', 'cancelled', 'unknown')", name="ck_thesis_catalysts_status"),
        sa.ForeignKeyConstraint(["thesis_id"], ["saved_theses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thesis_catalysts_thesis_date", "thesis_catalysts", ["thesis_id", "expected_date"])
    op.create_index("ix_thesis_catalysts_owner_created", "thesis_catalysts", ["owner_user_id", "created_at"])
    op.create_index("ix_thesis_catalysts_org_created", "thesis_catalysts", ["organization_id", "created_at"])

    op.create_table(
        "research_report_comparisons",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("left_report_id", sa.String(length=64), nullable=False),
        sa.Column("right_report_id", sa.String(length=64), nullable=False),
        sa.Column("left_input_checksum", sa.String(length=64), nullable=False),
        sa.Column("right_input_checksum", sa.String(length=64), nullable=False),
        sa.Column("scope_class", sa.String(length=16), nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("comparison_json", sa.JSON(), nullable=False),
        sa.Column("lineage_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope_class IN ('private', 'organization')", name="ck_research_report_comparisons_scope"),
        sa.CheckConstraint("schema_version = 'research_comparison.v1'", name="ck_research_report_comparisons_schema"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("left_report_id", "right_report_id", "scope_key", name="uq_research_report_comparisons_inputs"),
    )
    op.create_index("ix_research_report_comparisons_owner_created", "research_report_comparisons", ["owner_user_id", "created_at"])
    op.create_index("ix_research_report_comparisons_org_created", "research_report_comparisons", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_research_report_comparisons_org_created", table_name="research_report_comparisons")
    op.drop_index("ix_research_report_comparisons_owner_created", table_name="research_report_comparisons")
    op.drop_table("research_report_comparisons")
    op.drop_index("ix_thesis_catalysts_org_created", table_name="thesis_catalysts")
    op.drop_index("ix_thesis_catalysts_owner_created", table_name="thesis_catalysts")
    op.drop_index("ix_thesis_catalysts_thesis_date", table_name="thesis_catalysts")
    op.drop_table("thesis_catalysts")
    op.drop_index("ix_thesis_assumption_heads_thesis", table_name="thesis_assumption_heads")
    op.drop_table("thesis_assumption_heads")
    op.drop_index("ix_thesis_assumptions_thesis_created", table_name="thesis_assumptions")
    op.drop_table("thesis_assumptions")
    op.drop_index("ix_thesis_revisions_org_created", table_name="thesis_revisions")
    op.drop_index("ix_thesis_revisions_owner_created", table_name="thesis_revisions")
    op.drop_index("ix_thesis_revisions_thesis_created", table_name="thesis_revisions")
    op.drop_table("thesis_revisions")
