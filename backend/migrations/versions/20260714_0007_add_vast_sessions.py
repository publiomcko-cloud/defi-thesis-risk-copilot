"""add vast sessions

Revision ID: 20260714_0007
Revises: 20260714_0006
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa


revision = "20260714_0007"
down_revision = "20260714_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vast_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("vast_instance_id", sa.String(length=128), nullable=True),
        sa.Column("vast_contract_id", sa.String(length=128), nullable=True),
        sa.Column("offer_id", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("image", sa.String(length=512), nullable=False),
        sa.Column("gpu_name", sa.String(length=128), nullable=True),
        sa.Column("hourly_cost_usd", sa.Float(), nullable=True),
        sa.Column("max_runtime_minutes", sa.Integer(), nullable=False),
        sa.Column("container_port", sa.Integer(), nullable=False),
        sa.Column("public_endpoint_url", sa.String(length=512), nullable=True),
        sa.Column("health_status", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleanup_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vast_sessions_status"), "vast_sessions", ["status"])
    op.create_index(op.f("ix_vast_sessions_vast_instance_id"), "vast_sessions", ["vast_instance_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_vast_sessions_vast_instance_id"), table_name="vast_sessions")
    op.drop_index(op.f("ix_vast_sessions_status"), table_name="vast_sessions")
    op.drop_table("vast_sessions")
