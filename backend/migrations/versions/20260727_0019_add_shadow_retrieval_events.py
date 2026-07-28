"""add privacy-safe durable retrieval events

Revision ID: 20260727_0019
Revises: 20260727_0018
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0019"
down_revision = "20260727_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_retrieval_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("scores_json", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("retriever_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latency_ms >= 0", name="ck_knowledge_retrieval_events_latency"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_retrieval_events_request_id", "knowledge_retrieval_events", ["request_id"])
    op.create_index("ix_knowledge_retrieval_events_user_id", "knowledge_retrieval_events", ["user_id"])
    op.create_index("ix_knowledge_retrieval_events_organization_id", "knowledge_retrieval_events", ["organization_id"])
    op.create_index("ix_knowledge_retrieval_events_query_hash", "knowledge_retrieval_events", ["query_hash"])
    op.create_index("ix_knowledge_retrieval_events_user_created", "knowledge_retrieval_events", ["user_id", "created_at"])
    op.create_index("ix_knowledge_retrieval_events_org_created", "knowledge_retrieval_events", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_retrieval_events_org_created", table_name="knowledge_retrieval_events")
    op.drop_index("ix_knowledge_retrieval_events_user_created", table_name="knowledge_retrieval_events")
    op.drop_index("ix_knowledge_retrieval_events_query_hash", table_name="knowledge_retrieval_events")
    op.drop_index("ix_knowledge_retrieval_events_organization_id", table_name="knowledge_retrieval_events")
    op.drop_index("ix_knowledge_retrieval_events_user_id", table_name="knowledge_retrieval_events")
    op.drop_index("ix_knowledge_retrieval_events_request_id", table_name="knowledge_retrieval_events")
    op.drop_table("knowledge_retrieval_events")
