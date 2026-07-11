"""add monitoring tables

Revision ID: 20260711_0002
Revises: 20260710_0001
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa


revision = "20260711_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_watches",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_watches_protocol"), "source_watches", ["protocol"])
    op.create_index(op.f("ix_source_watches_source"), "source_watches", ["source"])

    op.create_table(
        "discovered_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("discovery_key", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("chain", sa.String(length=64), nullable=True),
        sa.Column("asset", sa.String(length=64), nullable=True),
        sa.Column("market_identifier", sa.String(length=255), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discovery_key", name="uq_discovered_items_discovery_key"),
    )
    op.create_index(
        op.f("ix_discovered_items_discovery_key"),
        "discovered_items",
        ["discovery_key"],
    )
    op.create_index(op.f("ix_discovered_items_protocol"), "discovered_items", ["protocol"])
    op.create_index(op.f("ix_discovered_items_source"), "discovered_items", ["source"])


def downgrade() -> None:
    op.drop_index(op.f("ix_discovered_items_source"), table_name="discovered_items")
    op.drop_index(op.f("ix_discovered_items_protocol"), table_name="discovered_items")
    op.drop_index(
        op.f("ix_discovered_items_discovery_key"),
        table_name="discovered_items",
    )
    op.drop_table("discovered_items")
    op.drop_index(op.f("ix_source_watches_source"), table_name="source_watches")
    op.drop_index(op.f("ix_source_watches_protocol"), table_name="source_watches")
    op.drop_table("source_watches")
