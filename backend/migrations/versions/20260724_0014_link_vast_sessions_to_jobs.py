"""link Vast provider sessions to durable jobs

Revision ID: 20260724_0014
Revises: 20260724_0013
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0014"
down_revision = "20260724_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vast_sessions") as batch:
        batch.add_column(sa.Column("source_job_id", sa.String(length=64), nullable=True))
        batch.create_foreign_key(
            "fk_vast_sessions_source_job_id_jobs",
            "jobs",
            ["source_job_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint("uq_vast_sessions_source_job", ["source_job_id"])
        batch.create_index("ix_vast_sessions_source_job_id", ["source_job_id"])


def downgrade() -> None:
    with op.batch_alter_table("vast_sessions") as batch:
        batch.drop_index("ix_vast_sessions_source_job_id")
        batch.drop_constraint("uq_vast_sessions_source_job", type_="unique")
        batch.drop_constraint("fk_vast_sessions_source_job_id_jobs", type_="foreignkey")
        batch.drop_column("source_job_id")
