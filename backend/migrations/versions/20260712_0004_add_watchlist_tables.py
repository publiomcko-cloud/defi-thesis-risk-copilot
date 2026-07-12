"""add watchlist tables

Revision ID: 20260712_0004
Revises: 20260711_0003
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa


revision = "20260712_0004"
down_revision = "20260711_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("market_identifier", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watchlist_items_item_type"), "watchlist_items", ["item_type"])
    op.create_index(op.f("ix_watchlist_items_protocol"), "watchlist_items", ["protocol"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("watchlist_item_id", sa.String(length=64), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("trigger_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watchlist_item_id"], ["watchlist_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_events_alert_type"), "alert_events", ["alert_type"])
    op.create_index(
        op.f("ix_alert_events_watchlist_item_id"),
        "alert_events",
        ["watchlist_item_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_alert_events_watchlist_item_id"), table_name="alert_events")
    op.drop_index(op.f("ix_alert_events_alert_type"), table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index(op.f("ix_watchlist_items_protocol"), table_name="watchlist_items")
    op.drop_index(op.f("ix_watchlist_items_item_type"), table_name="watchlist_items")
    op.drop_table("watchlist_items")
