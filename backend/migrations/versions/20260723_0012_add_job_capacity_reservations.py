"""add job capacity reservations

Revision ID: 20260723_0012
Revises: 20260723_0011
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0012"
down_revision = "20260723_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_capacity_reservations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=False),
        sa.Column("pending_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("running_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("budget_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budget_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope_type IN ('global', 'user', 'organization', 'provider')", name="ck_job_capacity_scope"),
        sa.CheckConstraint("pending_count >= 0", name="ck_job_capacity_pending"),
        sa.CheckConstraint("running_count >= 0", name="ck_job_capacity_running"),
        sa.CheckConstraint("reserved_cost_microusd >= 0", name="ck_job_capacity_reserved_cost"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "scope_id", name="uq_job_capacity_scope"),
    )
    op.create_index("ix_job_capacity_reservations_scope_type", "job_capacity_reservations", ["scope_type"])
    op.create_index("ix_job_capacity_reservations_scope_id", "job_capacity_reservations", ["scope_id"])


def downgrade() -> None:
    op.drop_index("ix_job_capacity_reservations_scope_id", table_name="job_capacity_reservations")
    op.drop_index("ix_job_capacity_reservations_scope_type", table_name="job_capacity_reservations")
    op.drop_table("job_capacity_reservations")
