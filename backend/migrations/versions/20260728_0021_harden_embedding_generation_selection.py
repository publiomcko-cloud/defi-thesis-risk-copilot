"""make durable retrieval select exact embedding generations

Revision ID: 20260728_0021
Revises: 20260728_0020
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0021"
down_revision = "20260728_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_document_versions",
        sa.Column("active_embedding_generation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_knowledge_document_versions_active_embedding_generation_id",
        "knowledge_document_versions",
        ["active_embedding_generation_id"],
    )
    # Phase 18D/18G wrote one completed generation per version/profile. The
    # deterministic backfill preserves that selection without rebuilding any
    # embeddings. Versions without a completed generation remain unselectable.
    op.execute(
        "UPDATE knowledge_document_versions "
        "SET active_embedding_generation_id = ("
        "  SELECT generation.id FROM knowledge_embedding_generations AS generation "
        "  WHERE generation.document_version_id = knowledge_document_versions.id "
        "    AND generation.embedding_profile_id = knowledge_document_versions.active_embedding_profile_id "
        "    AND generation.status = 'completed' "
        "    AND generation.deleted_at IS NULL "
        "  ORDER BY generation.completed_at DESC, generation.created_at DESC, generation.id DESC "
        "  LIMIT 1"
        ") "
        "WHERE active_embedding_generation_id IS NULL"
    )

    with op.batch_alter_table("knowledge_embedding_generations") as batch:
        batch.drop_constraint(
            "uq_knowledge_embedding_generations_version_profile", type_="unique"
        )
        batch.create_index(
            "ix_knowledge_embedding_generations_version_profile_status",
            ["document_version_id", "embedding_profile_id", "status"],
            unique=False,
        )
    with op.batch_alter_table("knowledge_chunk_embeddings") as batch:
        batch.drop_constraint(
            "uq_knowledge_chunk_embeddings_chunk_profile", type_="unique"
        )
        batch.create_unique_constraint(
            "uq_knowledge_chunk_embeddings_chunk_generation",
            ["knowledge_chunk_id", "embedding_generation_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    duplicate_generations = bind.execute(
        sa.text(
            "SELECT 1 FROM knowledge_embedding_generations "
            "GROUP BY document_version_id, embedding_profile_id HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    duplicate_embeddings = bind.execute(
        sa.text(
            "SELECT 1 FROM knowledge_chunk_embeddings "
            "GROUP BY knowledge_chunk_id, embedding_profile_id HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate_generations or duplicate_embeddings:
        raise RuntimeError(
            "Cannot downgrade Phase 18 generation storage while multiple generation "
            "rows exist for the same profile. Retain the Phase 18 schema or archive "
            "the additional generations explicitly."
        )

    with op.batch_alter_table("knowledge_chunk_embeddings") as batch:
        batch.drop_constraint(
            "uq_knowledge_chunk_embeddings_chunk_generation", type_="unique"
        )
        batch.create_unique_constraint(
            "uq_knowledge_chunk_embeddings_chunk_profile",
            ["knowledge_chunk_id", "embedding_profile_id"],
        )
    with op.batch_alter_table("knowledge_embedding_generations") as batch:
        batch.drop_index("ix_knowledge_embedding_generations_version_profile_status")
        batch.create_unique_constraint(
            "uq_knowledge_embedding_generations_version_profile",
            ["document_version_id", "embedding_profile_id"],
        )
    op.drop_index(
        "ix_knowledge_document_versions_active_embedding_generation_id",
        table_name="knowledge_document_versions",
    )
    op.drop_column("knowledge_document_versions", "active_embedding_generation_id")
