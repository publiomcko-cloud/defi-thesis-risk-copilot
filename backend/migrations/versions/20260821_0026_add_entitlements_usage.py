"""add Phase 20F entitlements and non-billable usage

Revision ID: 20260821_0026
Revises: 20260814_0025
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0026"
down_revision = "20260814_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("plan_key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_key", "version", name="uq_plan_versions_key_version"),
    )
    op.create_index("ix_plan_versions_plan_key", "plan_versions", ["plan_key"])
    op.create_table(
        "plan_entitlements",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("plan_version_id", sa.String(length=64), nullable=False),
        sa.Column("entitlement_key", sa.String(length=96), nullable=False),
        sa.Column("hard_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_version_id", "entitlement_key", name="uq_plan_entitlements_version_key"),
    )
    op.create_table(
        "entitlement_assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=16), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("plan_version_id", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("subject_type = 'user'", name="ck_entitlement_assignments_user_only"),
        sa.ForeignKeyConstraint(["subject_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_version_id"], ["plan_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_type", "subject_id", "plan_version_id", "effective_from", name="uq_entitlement_assignment_identity"),
    )
    op.create_index("ix_entitlement_assignments_resolver", "entitlement_assignments", ["subject_type", "subject_id", "effective_from", "effective_until"])
    op.create_table(
        "non_billable_usage_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("unit_key", sa.String(length=96), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("logical_key", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reverses_event_id", sa.String(length=64), nullable=True),
        sa.Column("correction_code", sa.String(length=48), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reverses_event_id"], ["non_billable_usage_events.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("unit_key IN ('usage.analysis.completed.v1', 'usage.simulation.completed.v1', 'usage.options.completed.v1', 'usage.schedule.run_completed.v1')", name="ck_non_billable_usage_unit_key"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_key", "logical_key", name="uq_non_billable_usage_unit_logical"),
        sa.UniqueConstraint("reverses_event_id", name="uq_non_billable_usage_reversal"),
    )
    op.create_index("ix_non_billable_usage_subject_unit", "non_billable_usage_events", ["owner_user_id", "unit_key", "occurred_at"])
    op.create_index("ix_non_billable_usage_source", "non_billable_usage_events", ["source_type", "source_id"])


def downgrade() -> None:
    op.drop_index("ix_non_billable_usage_source", table_name="non_billable_usage_events")
    op.drop_index("ix_non_billable_usage_subject_unit", table_name="non_billable_usage_events")
    op.drop_table("non_billable_usage_events")
    op.drop_index("ix_entitlement_assignments_resolver", table_name="entitlement_assignments")
    op.drop_table("entitlement_assignments")
    op.drop_table("plan_entitlements")
    op.drop_index("ix_plan_versions_plan_key", table_name="plan_versions")
    op.drop_table("plan_versions")
