"""add bounded model governance

Revision ID: 20260904_0030
Revises: 20260828_0029
Create Date: 2026-09-04
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260904_0030"
down_revision = "20260828_0029"
branch_labels = None
depends_on = None


TASK_KEY_CHECK = (
    "task_key IN ('report_synthesis', 'strategy_parsing', 'source_classification', "
    "'retrieval_reranking', 'entity_extraction', 'scenario_explanation', "
    "'research_summarization')"
)
PROMPT_CHECKSUM = "9ac1e2188d270720550406823cdaed68c929b0cdc4bb248b18b3f95191ab3516"


def upgrade() -> None:
    op.create_table(
        "model_registry",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("model_key", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("endpoint_class", sa.String(length=32), nullable=False),
        sa.Column("privacy_classification", sa.String(length=32), nullable=False),
        sa.Column("max_context_tokens", sa.Integer(), nullable=True),
        sa.Column("input_cost_microusd_per_million", sa.Integer(), nullable=True),
        sa.Column("output_cost_microusd_per_million", sa.Integer(), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("evaluation_state", sa.String(length=32), nullable=False),
        sa.Column("promotion_state", sa.String(length=32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(provider_key) BETWEEN 1 AND 64", name="ck_model_registry_provider_key"),
        sa.CheckConstraint("length(model_key) BETWEEN 1 AND 128", name="ck_model_registry_model_key"),
        sa.CheckConstraint("length(model_version) BETWEEN 1 AND 128", name="ck_model_registry_model_version"),
        sa.CheckConstraint("endpoint_class IN ('ollama_generate', 'openai_compatible_chat', 'custom')", name="ck_model_registry_endpoint"),
        sa.CheckConstraint("privacy_classification IN ('unknown', 'public_only', 'private_approved')", name="ck_model_registry_privacy"),
        sa.CheckConstraint("lifecycle_state IN ('registered', 'candidate', 'promoted', 'retired')", name="ck_model_registry_lifecycle"),
        sa.CheckConstraint("evaluation_state IN ('not_evaluated', 'evaluated')", name="ck_model_registry_evaluation"),
        sa.CheckConstraint("promotion_state IN ('not_promoted', 'promoted', 'rolled_back')", name="ck_model_registry_promotion"),
        sa.CheckConstraint("max_context_tokens IS NULL OR max_context_tokens BETWEEN 1 AND 10000000", name="ck_model_registry_context"),
        sa.CheckConstraint("input_cost_microusd_per_million IS NULL OR input_cost_microusd_per_million >= 0", name="ck_model_registry_input_cost"),
        sa.CheckConstraint("output_cost_microusd_per_million IS NULL OR output_cost_microusd_per_million >= 0", name="ck_model_registry_output_cost"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_key", "model_key", "model_version", "endpoint_class", name="uq_model_registry_identity"),
    )
    op.create_index("ix_model_registry_lifecycle", "model_registry", ["lifecycle_state", "created_at"])

    op.create_table(
        "model_task_capabilities",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("model_registry_id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("capability_state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_task_capabilities_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_task_capabilities_version"),
        sa.CheckConstraint("capability_state IN ('registered', 'disabled')", name="ck_model_task_capabilities_state"),
        sa.ForeignKeyConstraint(["model_registry_id"], ["model_registry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_registry_id", "task_key", "task_version", name="uq_model_task_capability"),
    )
    op.create_index("ix_model_task_capabilities_task", "model_task_capabilities", ["task_key", "task_version"])

    op.create_table(
        "model_prompt_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("output_schema_version", sa.String(length=64), nullable=False),
        sa.Column("safety_policy_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_prompt_versions_task_key"),
        sa.CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_prompt_versions_task_version"),
        sa.CheckConstraint("length(prompt_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_prompt_version"),
        sa.CheckConstraint("length(output_schema_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_schema_version"),
        sa.CheckConstraint("length(safety_policy_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_safety_version"),
        sa.CheckConstraint("length(prompt_checksum) = 64", name="ck_model_prompt_versions_checksum"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_key", "task_version", "prompt_version", name="uq_model_prompt_task_version"),
        sa.UniqueConstraint("prompt_checksum", name="uq_model_prompt_checksum"),
    )

    op.create_table(
        "model_run_provenance",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=64), nullable=False),
        sa.Column("task_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_version_id", sa.String(length=64), nullable=False),
        sa.Column("model_registry_id", sa.String(length=64), nullable=True),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("anonymous_session_id", sa.String(length=128), nullable=True),
        sa.Column("scope_class", sa.String(length=16), nullable=False),
        sa.Column("deterministic_input_checksum", sa.String(length=64), nullable=False),
        sa.Column("retrieval_digest", sa.String(length=64), nullable=True),
        sa.Column("retrieval_source_count", sa.Integer(), nullable=False),
        sa.Column("validation_result", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("fallback_reason", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_microusd", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(TASK_KEY_CHECK, name="ck_model_run_provenance_task_key"),
        sa.CheckConstraint("scope_class IN ('public', 'private', 'organization', 'anonymous')", name="ck_model_run_provenance_scope"),
        sa.CheckConstraint("outcome IN ('disabled', 'provider_unavailable', 'succeeded', 'validation_fallback', 'provider_failure')", name="ck_model_run_provenance_outcome"),
        sa.CheckConstraint("validation_result IN ('not_run', 'accepted', 'invalid_json', 'schema_invalid', 'unsafe_output', 'provider_error', 'policy_denied')", name="ck_model_run_provenance_validation"),
        sa.CheckConstraint("fallback_reason IS NULL OR length(fallback_reason) BETWEEN 1 AND 64", name="ck_model_run_provenance_fallback"),
        sa.CheckConstraint("length(deterministic_input_checksum) = 64", name="ck_model_run_provenance_input_checksum"),
        sa.CheckConstraint("retrieval_digest IS NULL OR length(retrieval_digest) = 64", name="ck_model_run_provenance_retrieval_digest"),
        sa.CheckConstraint("retrieval_source_count BETWEEN 0 AND 64", name="ck_model_run_provenance_retrieval_count"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms BETWEEN 0 AND 3600000", name="ck_model_run_provenance_latency"),
        sa.CheckConstraint("input_tokens IS NULL OR input_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_input_tokens"),
        sa.CheckConstraint("output_tokens IS NULL OR output_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_output_tokens"),
        sa.CheckConstraint("total_tokens IS NULL OR total_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_total_tokens"),
        sa.CheckConstraint("cost_microusd IS NULL OR cost_microusd >= 0", name="ck_model_run_provenance_cost"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["model_prompt_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_registry_id"], ["model_registry.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["anonymous_session_id"], ["anonymous_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "task_key", "task_version", name="uq_model_run_report_task"),
    )
    op.create_index("ix_model_run_provenance_owner_created", "model_run_provenance", ["owner_user_id", "created_at"])
    op.create_index("ix_model_run_provenance_org_created", "model_run_provenance", ["organization_id", "created_at"])
    op.create_index("ix_model_run_provenance_anonymous", "model_run_provenance", ["anonymous_session_id", "created_at"])

    timestamp = datetime(2026, 9, 4, tzinfo=UTC)
    op.bulk_insert(
        sa.table(
            "model_prompt_versions",
            sa.column("id", sa.String),
            sa.column("task_key", sa.String),
            sa.column("task_version", sa.String),
            sa.column("prompt_version", sa.String),
            sa.column("output_schema_version", sa.String),
            sa.column("safety_policy_version", sa.String),
            sa.column("prompt_checksum", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "prompt_report_synthesis_v1",
                "task_key": "report_synthesis",
                "task_version": "v1",
                "prompt_version": "report_synthesis.prompt.v1",
                "output_schema_version": "report_synthesis.output.v1",
                "safety_policy_version": "report_synthesis.safety.v1",
                "prompt_checksum": PROMPT_CHECKSUM,
                "created_at": timestamp,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_model_run_provenance_anonymous", table_name="model_run_provenance")
    op.drop_index("ix_model_run_provenance_org_created", table_name="model_run_provenance")
    op.drop_index("ix_model_run_provenance_owner_created", table_name="model_run_provenance")
    op.drop_table("model_run_provenance")
    op.drop_table("model_prompt_versions")
    op.drop_index("ix_model_task_capabilities_task", table_name="model_task_capabilities")
    op.drop_table("model_task_capabilities")
    op.drop_index("ix_model_registry_lifecycle", table_name="model_registry")
    op.drop_table("model_registry")
