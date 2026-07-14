"""add knowledge base ingestions

Revision ID: 20260714_0005
Revises: 20260712_0004
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa


revision = "20260714_0005"
down_revision = "20260712_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_ingestions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("review_item_id", sa.String(length=64), nullable=False),
        sa.Column("generated_markdown_path", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_by", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_item_id",
            name="uq_knowledge_base_ingestions_review_item_id",
        ),
    )
    op.create_index(
        op.f("ix_knowledge_base_ingestions_protocol"),
        "knowledge_base_ingestions",
        ["protocol"],
    )
    op.create_index(
        op.f("ix_knowledge_base_ingestions_review_item_id"),
        "knowledge_base_ingestions",
        ["review_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_knowledge_base_ingestions_review_item_id"),
        table_name="knowledge_base_ingestions",
    )
    op.drop_index(
        op.f("ix_knowledge_base_ingestions_protocol"),
        table_name="knowledge_base_ingestions",
    )
    op.drop_table("knowledge_base_ingestions")
