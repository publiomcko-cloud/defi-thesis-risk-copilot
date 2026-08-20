"""add in-app notifications

Revision ID: 20260814_0025
Revises: 20260813_0024
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260814_0025"
down_revision = "20260813_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("category_enabled_json", sa.JSON(), nullable=False),
        sa.Column("minimum_severity_json", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=5), nullable=True),
        sa.Column("daily_digest_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quiet_hours_start IS NULL OR (length(quiet_hours_start) = 5 AND substr(quiet_hours_start, 3, 1) = ':' AND quiet_hours_start >= '00:00' AND quiet_hours_start <= '23:59')", name="ck_notification_preferences_quiet_start"),
        sa.CheckConstraint("quiet_hours_end IS NULL OR (length(quiet_hours_end) = 5 AND substr(quiet_hours_end, 3, 1) = ':' AND quiet_hours_end >= '00:00' AND quiet_hours_end <= '23:59')", name="ck_notification_preferences_quiet_end"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("template_id", sa.String(length=96), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("navigation_json", sa.JSON(), nullable=False),
        sa.Column("policy_outcome", sa.String(length=32), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('monitoring.risk_alert', 'schedule.status', 'job.status', 'account.lifecycle')", name="ck_notifications_category"),
        sa.CheckConstraint("severity IN ('informational', 'warning', 'critical')", name="ck_notifications_severity"),
        sa.CheckConstraint("policy_outcome IN ('available', 'delayed_quiet_hours', 'delayed_digest', 'suppressed_by_preference', 'mandatory')", name="ck_notifications_policy_outcome"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "idempotency_key", name="uq_notifications_owner_idempotency"),
    )
    op.create_index("ix_notifications_owner_user_id", "notifications", ["owner_user_id"])
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_owner_available", "notifications", ["owner_user_id", "available_at", "created_at"])
    op.create_index("ix_notifications_owner_unread", "notifications", ["owner_user_id", "read_at", "available_at"])
    op.create_index("ix_notifications_retention", "notifications", ["expires_at"])
    op.create_index("ix_notifications_source", "notifications", ["source_type", "source_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_source", table_name="notifications")
    op.drop_index("ix_notifications_retention", table_name="notifications")
    op.drop_index("ix_notifications_owner_unread", table_name="notifications")
    op.drop_index("ix_notifications_owner_available", table_name="notifications")
    op.drop_index("ix_notifications_organization_id", table_name="notifications")
    op.drop_index("ix_notifications_owner_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
