"""Add persisted thesis research-run linkage and bounded-run metadata.

Revision ID: 20261022_0035
Revises: 20260911_0034
"""

from alembic import op
import sqlalchemy as sa


revision = "20261022_0035"
down_revision = "20260911_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_requests") as batch:
        batch.add_column(sa.Column("thesis_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("research_question", sa.Text(), nullable=True))
        batch.add_column(sa.Column("research_run_key", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("research_input_checksum", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("research_status", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("research_metadata_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("research_completed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_analysis_requests_thesis_id_saved_theses",
            "saved_theses",
            ["thesis_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint(
            "uq_analysis_requests_owner_research_key",
            ["owner_user_id", "research_run_key"],
        )
    op.create_index("ix_analysis_requests_thesis_id", "analysis_requests", ["thesis_id"])
    op.create_index(
        "ix_analysis_requests_thesis_created",
        "analysis_requests",
        ["thesis_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_requests_thesis_created", table_name="analysis_requests")
    op.drop_index("ix_analysis_requests_thesis_id", table_name="analysis_requests")
    with op.batch_alter_table("analysis_requests") as batch:
        batch.drop_constraint("uq_analysis_requests_owner_research_key", type_="unique")
        batch.drop_constraint("fk_analysis_requests_thesis_id_saved_theses", type_="foreignkey")
        batch.drop_column("research_metadata_json")
        batch.drop_column("research_completed_at")
        batch.drop_column("research_status")
        batch.drop_column("research_input_checksum")
        batch.drop_column("research_run_key")
        batch.drop_column("research_question")
        batch.drop_column("thesis_id")
