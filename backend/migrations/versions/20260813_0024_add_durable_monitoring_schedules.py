"""add durable user-owned monitoring schedules

Revision ID: 20260813_0024
Revises: 20260731_0023
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0024"
down_revision = "20260731_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitoring_schedules",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("cadence", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'paused', 'deleted')", name="ck_monitoring_schedules_status"),
        sa.CheckConstraint("target_type = 'watchlist.evaluate'", name="ck_monitoring_schedules_target_type"),
        sa.CheckConstraint(
            "cadence IN ('hourly', 'six_hourly', 'daily', 'weekly')",
            name="ck_monitoring_schedules_cadence",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitoring_schedules_due", "monitoring_schedules", ["status", "next_due_at", "deleted_at"])
    op.create_index("ix_monitoring_schedules_owner_status", "monitoring_schedules", ["owner_user_id", "status", "deleted_at"])
    op.create_index("ix_monitoring_schedules_owner_user_id", "monitoring_schedules", ["owner_user_id"])
    op.create_index("ix_monitoring_schedules_target_id", "monitoring_schedules", ["target_id"])

    op.create_table(
        "monitoring_schedule_occurrences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schedule_id", sa.String(length=64), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('claimed', 'queued', 'running', 'completed', 'failed', 'denied', 'missed', 'cancel_requested', 'cancelled')",
            name="ck_monitoring_schedule_occurrences_status",
        ),
        sa.ForeignKeyConstraint(["schedule_id"], ["monitoring_schedules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "scheduled_for", name="uq_monitoring_schedule_occurrence_time"),
    )
    op.create_index("ix_monitoring_schedule_occurrences_schedule_time", "monitoring_schedule_occurrences", ["schedule_id", "scheduled_for"])
    op.create_index("ix_monitoring_schedule_occurrences_expiry", "monitoring_schedule_occurrences", ["expires_at"])
    op.create_index("ix_monitoring_schedule_occurrences_job", "monitoring_schedule_occurrences", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_monitoring_schedule_occurrences_job", table_name="monitoring_schedule_occurrences")
    op.drop_index("ix_monitoring_schedule_occurrences_expiry", table_name="monitoring_schedule_occurrences")
    op.drop_index("ix_monitoring_schedule_occurrences_schedule_time", table_name="monitoring_schedule_occurrences")
    op.drop_table("monitoring_schedule_occurrences")
    op.drop_index("ix_monitoring_schedules_target_id", table_name="monitoring_schedules")
    op.drop_index("ix_monitoring_schedules_owner_user_id", table_name="monitoring_schedules")
    op.drop_index("ix_monitoring_schedules_owner_status", table_name="monitoring_schedules")
    op.drop_index("ix_monitoring_schedules_due", table_name="monitoring_schedules")
    op.drop_table("monitoring_schedules")
