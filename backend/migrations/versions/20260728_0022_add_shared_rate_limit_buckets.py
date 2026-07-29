"""add shared rate-limit buckets

Revision ID: 20260728_0022
Revises: 20260728_0021
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0022"
down_revision = "20260728_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key_hash", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_value", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('ip', 'session', 'user', 'organization')",
            name="ck_rate_limit_buckets_scope_type",
        ),
        sa.CheckConstraint("window_seconds > 0", name="ck_rate_limit_buckets_window_seconds"),
        sa.CheckConstraint("request_count >= 0", name="ck_rate_limit_buckets_request_count"),
        sa.CheckConstraint("limit_value > 0", name="ck_rate_limit_buckets_limit_value"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope_type",
            "scope_key_hash",
            "action",
            "window_seconds",
            "window_started_at",
            name="uq_rate_limit_buckets_scope_window",
        ),
    )
    op.create_index("ix_rate_limit_buckets_scope_type", "rate_limit_buckets", ["scope_type"])
    op.create_index("ix_rate_limit_buckets_scope_key_hash", "rate_limit_buckets", ["scope_key_hash"])
    op.create_index("ix_rate_limit_buckets_action", "rate_limit_buckets", ["action"])
    op.create_index("ix_rate_limit_buckets_expiry", "rate_limit_buckets", ["expires_at"])
    op.create_index(
        "ix_rate_limit_buckets_action_expiry",
        "rate_limit_buckets",
        ["action", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_buckets_action_expiry", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_expiry", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_action", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_scope_key_hash", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_scope_type", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
