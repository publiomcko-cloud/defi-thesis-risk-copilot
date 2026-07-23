"""add organization knowledge source metadata

Revision ID: 20260721_0009
Revises: 20260720_0008
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa


revision = "20260721_0009"
down_revision = "20260720_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_knowledge_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("provenance_hash", sa.String(length=128), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("storage_status", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "source_url",
            name="uq_organization_knowledge_source_url",
        ),
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_approval_status"),
        "organization_knowledge_sources",
        ["approval_status"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_approved_by_user_id"),
        "organization_knowledge_sources",
        ["approved_by_user_id"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_created_by_user_id"),
        "organization_knowledge_sources",
        ["created_by_user_id"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_organization_id"),
        "organization_knowledge_sources",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_protocol"),
        "organization_knowledge_sources",
        ["protocol"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_status"),
        "organization_knowledge_sources",
        ["status"],
    )
    op.create_index(
        op.f("ix_organization_knowledge_sources_storage_status"),
        "organization_knowledge_sources",
        ["storage_status"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_knowledge_sources_storage_status"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_status"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_protocol"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_organization_id"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_created_by_user_id"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_approved_by_user_id"),
        table_name="organization_knowledge_sources",
    )
    op.drop_index(
        op.f("ix_organization_knowledge_sources_approval_status"),
        table_name="organization_knowledge_sources",
    )
    op.drop_table("organization_knowledge_sources")
