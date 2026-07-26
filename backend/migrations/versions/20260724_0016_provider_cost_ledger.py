"""add durable provider cost ledger

Revision ID: 20260724_0016
Revises: 20260724_0015
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0016"
down_revision = "20260724_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_cost_reservations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("actual_cost_microusd", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="reserved"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reserved_cost_microusd >= 0", name="ck_provider_cost_reserved"),
        sa.CheckConstraint("actual_cost_microusd >= 0", name="ck_provider_cost_actual"),
        sa.CheckConstraint("status IN ('reserved', 'running', 'completed', 'released', 'cancelled', 'reconciliation_required')", name="ck_provider_cost_status"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_provider_cost_reservations_job"),
    )
    op.create_index("ix_provider_cost_reservations_job_id", "provider_cost_reservations", ["job_id"])
    op.create_index("ix_provider_cost_reservations_status", "provider_cost_reservations", ["status"])
    op.create_index(
        "ix_provider_cost_reservations_period_status",
        "provider_cost_reservations",
        ["provider", "period_start", "period_end", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_cost_reservations_period_status", table_name="provider_cost_reservations")
    op.drop_index("ix_provider_cost_reservations_status", table_name="provider_cost_reservations")
    op.drop_index("ix_provider_cost_reservations_job_id", table_name="provider_cost_reservations")
    op.drop_table("provider_cost_reservations")
