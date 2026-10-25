"""Add isolated research-GPU policy binding and cold/warm evidence.

Revision ID: 20261025_0037
Revises: 20261022_0036
"""

from alembic import op
import sqlalchemy as sa


revision = "20261025_0037"
down_revision = "20261022_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_evaluation_runs") as batch:
        batch.add_column(sa.Column("evaluation_binding_checksum", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("evaluation_binding_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("cold_latency_count", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("cold_latency_total_ms", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("warm_latency_count", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("warm_latency_total_ms", sa.Integer(), server_default="0", nullable=False))
        batch.create_check_constraint(
            "ck_model_evaluation_runs_binding_checksum",
            "evaluation_binding_checksum IS NULL OR length(evaluation_binding_checksum) = 64",
        )
        batch.create_check_constraint(
            "ck_model_evaluation_runs_binding_pair",
            "(evaluation_binding_checksum IS NULL AND evaluation_binding_json IS NULL) OR "
            "(evaluation_binding_checksum IS NOT NULL AND evaluation_binding_json IS NOT NULL)",
        )
        batch.create_check_constraint("ck_model_evaluation_runs_cold_latency_count", "cold_latency_count BETWEEN 0 AND case_count")
        batch.create_check_constraint("ck_model_evaluation_runs_cold_latency_total", "cold_latency_total_ms >= 0")
        batch.create_check_constraint("ck_model_evaluation_runs_warm_latency_count", "warm_latency_count BETWEEN 0 AND case_count")
        batch.create_check_constraint("ck_model_evaluation_runs_warm_latency_total", "warm_latency_total_ms >= 0")

    with op.batch_alter_table("model_evaluation_case_results") as batch:
        batch.add_column(sa.Column("latency_phase", sa.String(length=16), nullable=True))
        batch.create_check_constraint(
            "ck_model_evaluation_case_results_latency_phase",
            "latency_phase IS NULL OR latency_phase IN ('cold', 'warm')",
        )


def downgrade() -> None:
    with op.batch_alter_table("model_evaluation_case_results") as batch:
        batch.drop_constraint("ck_model_evaluation_case_results_latency_phase", type_="check")
        batch.drop_column("latency_phase")

    with op.batch_alter_table("model_evaluation_runs") as batch:
        batch.drop_constraint("ck_model_evaluation_runs_warm_latency_total", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_warm_latency_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_cold_latency_total", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_cold_latency_count", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_binding_pair", type_="check")
        batch.drop_constraint("ck_model_evaluation_runs_binding_checksum", type_="check")
        batch.drop_column("warm_latency_total_ms")
        batch.drop_column("warm_latency_count")
        batch.drop_column("cold_latency_total_ms")
        batch.drop_column("cold_latency_count")
        batch.drop_column("evaluation_binding_json")
        batch.drop_column("evaluation_binding_checksum")
