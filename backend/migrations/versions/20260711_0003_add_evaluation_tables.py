"""add evaluation tables

Revision ID: 20260711_0003
Revises: 20260711_0002
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa


revision = "20260711_0003"
down_revision = "20260711_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("discovered_item_id", sa.String(length=64), nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("risk_rating", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("risk_summary", sa.Text(), nullable=False),
        sa.Column("missing_data_json", sa.JSON(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["discovered_item_id"], ["discovered_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_results_discovered_item_id"),
        "evaluation_results",
        ["discovered_item_id"],
    )

    op.create_table(
        "review_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("discovered_item_id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_result_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("prepared_for_rag", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["discovered_item_id"], ["discovered_items.id"]),
        sa.ForeignKeyConstraint(["evaluation_result_id"], ["evaluation_results.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discovered_item_id", name="uq_review_items_discovered_item_id"),
    )
    op.create_index(
        op.f("ix_review_items_discovered_item_id"),
        "review_items",
        ["discovered_item_id"],
    )
    op.create_index(
        op.f("ix_review_items_evaluation_result_id"),
        "review_items",
        ["evaluation_result_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_items_evaluation_result_id"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_discovered_item_id"), table_name="review_items")
    op.drop_table("review_items")
    op.drop_index(
        op.f("ix_evaluation_results_discovered_item_id"),
        table_name="evaluation_results",
    )
    op.drop_table("evaluation_results")
