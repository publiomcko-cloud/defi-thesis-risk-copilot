"""Keep the provider-reported token total beside the enforced effective total.

Revision ID: 20261022_0036
Revises: 20261022_0035
"""

from alembic import op
import sqlalchemy as sa


revision = "20261022_0036"
down_revision = "20261022_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_run_provenance") as batch:
        batch.add_column(sa.Column("reported_total_tokens", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            "ck_model_run_provenance_reported_total_tokens",
            "reported_total_tokens IS NULL OR reported_total_tokens BETWEEN 0 AND 10000000",
        )


def downgrade() -> None:
    with op.batch_alter_table("model_run_provenance") as batch:
        batch.drop_constraint("ck_model_run_provenance_reported_total_tokens", type_="check")
        batch.drop_column("reported_total_tokens")
