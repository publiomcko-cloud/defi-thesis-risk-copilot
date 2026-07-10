"""add initial tables

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("strategy_description", sa.Text(), nullable=False),
        sa.Column("protocols", sa.JSON(), nullable=False),
        sa.Column("market_url", sa.Text(), nullable=True),
        sa.Column("manual_inputs_json", sa.JSON(), nullable=False),
        sa.Column("analysis_depth", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "market_data_cache",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_market_data_cache_cache_key"),
        "market_data_cache",
        ["cache_key"],
        unique=False,
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("analysis_request_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("risk_rating", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_request_id"], ["analysis_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_index(op.f("ix_market_data_cache_cache_key"), table_name="market_data_cache")
    op.drop_table("market_data_cache")
    op.drop_table("document_sources")
    op.drop_table("analysis_requests")
