"""add evaluated model routing

Revision ID: 20260906_0031
Revises: 20260904_0030
Create Date: 2026-09-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260906_0031"
down_revision = "20260904_0030"
branch_labels = None
depends_on = None


TASK_KEY_CHECK = (
    "task_key IN ('report_synthesis', 'strategy_parsing', 'source_classification', "
    "'retrieval_reranking', 'entity_extraction', 'scenario_explanation', "
    "'research_summarization')"
)
ENVIRONMENT_CHECK = "environment IN ('development', 'test', 'staging', 'production', 'portfolio_demo', 'exercise')"


def upgrade() -> None:
    op.create_table(
        "model_evaluation_datasets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_evaluation_datasets_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_evaluation_datasets_task_version"),
        sa.CheckConstraint("length(dataset_version) BETWEEN 1 AND 64", name="ck_model_evaluation_datasets_version"),
        sa.CheckConstraint("length(purpose) BETWEEN 1 AND 128", name="ck_model_evaluation_datasets_purpose"),
        sa.CheckConstraint("length(dataset_checksum) = 64", name="ck_model_evaluation_datasets_checksum"),
        sa.CheckConstraint("case_count BETWEEN 1 AND 1000", name="ck_model_evaluation_datasets_case_count"),
        sa.CheckConstraint("lifecycle_state IN ('active', 'retired')", name="ck_model_evaluation_datasets_lifecycle"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_key", "task_version", "dataset_version", name="uq_model_evaluation_dataset_version"),
        sa.UniqueConstraint("dataset_checksum", name="uq_model_evaluation_dataset_checksum"),
    )
    op.create_index("ix_model_evaluation_datasets_task", "model_evaluation_datasets", ["task_key", "task_version", "created_at"])

    op.create_table(
        "model_evaluation_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_model_registry_id", sa.String(length=64), nullable=False),
        sa.Column("baseline_type", sa.String(length=32), nullable=False),
        sa.Column("baseline_model_registry_id", sa.String(length=64), nullable=True),
        sa.Column("baseline_route_version_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_version_id", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("policy_checksum", sa.String(length=64), nullable=False),
        sa.Column("code_revision", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("passed_case_count", sa.Integer(), nullable=False),
        sa.Column("structured_output_valid_count", sa.Integer(), nullable=False),
        sa.Column("deterministic_preserved_count", sa.Integer(), nullable=False),
        sa.Column("source_integrity_count", sa.Integer(), nullable=False),
        sa.Column("missing_data_honesty_count", sa.Integer(), nullable=False),
        sa.Column("unsafe_language_violation_count", sa.Integer(), nullable=False),
        sa.Column("privacy_policy_violation_count", sa.Integer(), nullable=False),
        sa.Column("provider_failure_count", sa.Integer(), nullable=False),
        sa.Column("latency_known_count", sa.Integer(), nullable=False),
        sa.Column("latency_total_ms", sa.Integer(), nullable=False),
        sa.Column("token_observation_count", sa.Integer(), nullable=False),
        sa.Column("input_tokens_total", sa.Integer(), nullable=False),
        sa.Column("output_tokens_total", sa.Integer(), nullable=False),
        sa.Column("total_tokens_total", sa.Integer(), nullable=False),
        sa.Column("cost_observation_count", sa.Integer(), nullable=False),
        sa.Column("cost_microusd_total", sa.Integer(), nullable=False),
        sa.Column("promotion_eligible", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_evaluation_runs_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_evaluation_runs_task_version"),
        sa.CheckConstraint(ENVIRONMENT_CHECK, name="ck_model_evaluation_runs_environment"),
        sa.CheckConstraint("baseline_type IN ('deterministic_fallback', 'promoted_route')", name="ck_model_evaluation_runs_baseline"),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_model_evaluation_runs_status"),
        sa.CheckConstraint("length(policy_version) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_policy_version"),
        sa.CheckConstraint("length(policy_checksum) = 64", name="ck_model_evaluation_runs_policy_checksum"),
        sa.CheckConstraint("length(code_revision) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_code_revision"),
        sa.CheckConstraint("case_count BETWEEN 0 AND 1000", name="ck_model_evaluation_runs_case_count"),
        sa.CheckConstraint("passed_case_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_passed_count"),
        sa.CheckConstraint("structured_output_valid_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_structure_count"),
        sa.CheckConstraint("deterministic_preserved_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_deterministic_count"),
        sa.CheckConstraint("source_integrity_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_source_count"),
        sa.CheckConstraint("missing_data_honesty_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_missing_count"),
        sa.CheckConstraint("unsafe_language_violation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_unsafe_count"),
        sa.CheckConstraint("privacy_policy_violation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_privacy_count"),
        sa.CheckConstraint("provider_failure_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_provider_failure_count"),
        sa.CheckConstraint("latency_known_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_latency_count"),
        sa.CheckConstraint("latency_total_ms >= 0", name="ck_model_evaluation_runs_latency_total"),
        sa.CheckConstraint("token_observation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_token_count"),
        sa.CheckConstraint("input_tokens_total >= 0 AND output_tokens_total >= 0 AND total_tokens_total >= 0", name="ck_model_evaluation_runs_token_totals"),
        sa.CheckConstraint("cost_observation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_cost_count"),
        sa.CheckConstraint("cost_microusd_total >= 0", name="ck_model_evaluation_runs_cost_total"),
        sa.CheckConstraint("failure_reason IS NULL OR length(failure_reason) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_failure_reason"),
        sa.ForeignKeyConstraint(["dataset_id"], ["model_evaluation_datasets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_model_registry_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_model_registry_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["model_prompt_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_evaluation_runs_candidate", "model_evaluation_runs", ["candidate_model_registry_id", "started_at"])
    op.create_index("ix_model_evaluation_runs_task_status", "model_evaluation_runs", ["task_key", "task_version", "environment", "status"])

    op.create_table(
        "model_evaluation_case_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("case_checksum", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("structured_output_valid", sa.Boolean(), nullable=False),
        sa.Column("deterministic_preserved", sa.Boolean(), nullable=False),
        sa.Column("source_integrity", sa.Boolean(), nullable=False),
        sa.Column("missing_data_honesty", sa.Boolean(), nullable=False),
        sa.Column("unsafe_language_violation", sa.Boolean(), nullable=False),
        sa.Column("privacy_policy_violation", sa.Boolean(), nullable=False),
        sa.Column("provider_failure", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_microusd", sa.Integer(), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(case_id) BETWEEN 1 AND 64", name="ck_model_evaluation_case_results_case_id"),
        sa.CheckConstraint("length(case_checksum) = 64", name="ck_model_evaluation_case_results_checksum"),
        sa.CheckConstraint("reason_code IS NULL OR length(reason_code) BETWEEN 1 AND 64", name="ck_model_evaluation_case_results_reason"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms BETWEEN 0 AND 3600000", name="ck_model_evaluation_case_results_latency"),
        sa.CheckConstraint("input_tokens IS NULL OR input_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_input_tokens"),
        sa.CheckConstraint("output_tokens IS NULL OR output_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_output_tokens"),
        sa.CheckConstraint("total_tokens IS NULL OR total_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_total_tokens"),
        sa.CheckConstraint("cost_microusd IS NULL OR cost_microusd >= 0", name="ck_model_evaluation_case_results_cost"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["model_evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "case_id", name="uq_model_evaluation_case_result"),
    )
    op.create_index("ix_model_evaluation_case_results_run", "model_evaluation_case_results", ["evaluation_run_id", "case_id"])

    op.create_table(
        "model_route_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("route_state", sa.String(length=32), nullable=False),
        sa.Column("model_registry_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_version_id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=64), nullable=False),
        sa.Column("previous_route_version_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_route_versions_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_route_versions_task_version"),
        sa.CheckConstraint(ENVIRONMENT_CHECK, name="ck_model_route_versions_environment"),
        sa.CheckConstraint("route_version > 0", name="ck_model_route_versions_version"),
        sa.CheckConstraint("route_state IN ('promoted')", name="ck_model_route_versions_state"),
        sa.ForeignKeyConstraint(["model_registry_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["model_prompt_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["model_evaluation_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_route_version_id"], ["model_route_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_key", "task_version", "environment", "route_version", name="uq_model_route_version"),
    )
    op.create_index("ix_model_route_versions_task", "model_route_versions", ["task_key", "task_version", "environment", "route_version"])

    op.create_table(
        "model_route_assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("active_route_version_id", sa.String(length=64), nullable=True),
        sa.Column("assignment_generation", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_route_assignments_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_route_assignments_task_version"),
        sa.CheckConstraint(ENVIRONMENT_CHECK, name="ck_model_route_assignments_environment"),
        sa.CheckConstraint("assignment_generation >= 0", name="ck_model_route_assignments_generation"),
        sa.ForeignKeyConstraint(["active_route_version_id"], ["model_route_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_key", "task_version", "environment", name="uq_model_route_assignment_scope"),
    )

    op.create_table(
        "model_route_transitions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("from_route_version_id", sa.String(length=64), nullable=True),
        sa.Column("to_route_version_id", sa.String(length=64), nullable=True),
        sa.Column("evaluation_run_id", sa.String(length=64), nullable=True),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("assignment_generation", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('promoted', 'rolled_back')", name="ck_model_route_transitions_action"),
        sa.CheckConstraint("reason_code IS NULL OR length(reason_code) BETWEEN 1 AND 64", name="ck_model_route_transitions_reason"),
        sa.CheckConstraint("assignment_generation >= 0", name="ck_model_route_transitions_generation"),
        sa.ForeignKeyConstraint(["assignment_id"], ["model_route_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["from_route_version_id"], ["model_route_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_route_version_id"], ["model_route_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["model_evaluation_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_route_transitions_assignment", "model_route_transitions", ["assignment_id", "created_at"])

    with op.batch_alter_table("model_run_provenance") as batch:
        batch.add_column(sa.Column("route_version_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("evaluation_run_id", sa.String(length=64), nullable=True))
        batch.create_foreign_key("fk_model_run_provenance_route_version", "model_route_versions", ["route_version_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_model_run_provenance_evaluation_run", "model_evaluation_runs", ["evaluation_run_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    with op.batch_alter_table("model_run_provenance") as batch:
        batch.drop_constraint("fk_model_run_provenance_evaluation_run", type_="foreignkey")
        batch.drop_constraint("fk_model_run_provenance_route_version", type_="foreignkey")
        batch.drop_column("evaluation_run_id")
        batch.drop_column("route_version_id")

    op.drop_index("ix_model_route_transitions_assignment", table_name="model_route_transitions")
    op.drop_table("model_route_transitions")
    op.drop_table("model_route_assignments")
    op.drop_index("ix_model_route_versions_task", table_name="model_route_versions")
    op.drop_table("model_route_versions")
    op.drop_index("ix_model_evaluation_case_results_run", table_name="model_evaluation_case_results")
    op.drop_table("model_evaluation_case_results")
    op.drop_index("ix_model_evaluation_runs_task_status", table_name="model_evaluation_runs")
    op.drop_index("ix_model_evaluation_runs_candidate", table_name="model_evaluation_runs")
    op.drop_table("model_evaluation_runs")
    op.drop_index("ix_model_evaluation_datasets_task", table_name="model_evaluation_datasets")
    op.drop_table("model_evaluation_datasets")
