"""harden durable job attempt lease and provider request state

Revision ID: 20260724_0015
Revises: 20260724_0014
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0015"
down_revision = "20260724_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_attempts") as batch:
        batch.add_column(sa.Column("max_lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_job_attempts_max_lease_expires_at", ["max_lease_expires_at"])
    with op.batch_alter_table("vast_sessions") as batch:
        batch.add_column(sa.Column("provider_request_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("provider_request_state", sa.String(length=64), nullable=True))
        batch.create_unique_constraint("uq_vast_sessions_provider_request_id", ["provider_request_id"])
        batch.create_index("ix_vast_sessions_provider_request_state", ["provider_request_state"])


def downgrade() -> None:
    with op.batch_alter_table("vast_sessions") as batch:
        batch.drop_index("ix_vast_sessions_provider_request_state")
        batch.drop_constraint("uq_vast_sessions_provider_request_id", type_="unique")
        batch.drop_column("provider_request_state")
        batch.drop_column("provider_request_id")
    with op.batch_alter_table("job_attempts") as batch:
        batch.drop_index("ix_job_attempts_max_lease_expires_at")
        batch.drop_column("max_lease_expires_at")
