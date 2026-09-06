from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


TASK_KEY_CHECK = (
    "task_key IN ('report_synthesis', 'strategy_parsing', 'source_classification', "
    "'retrieval_reranking', 'entity_extraction', 'scenario_explanation', "
    "'research_summarization')"
)


class ModelRegistryModel(Base):
    """Server-owned model metadata; credentials remain in provider settings."""

    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint(
            "provider_key",
            "model_key",
            "model_version",
            "endpoint_class",
            name="uq_model_registry_identity",
        ),
        CheckConstraint("length(provider_key) BETWEEN 1 AND 64", name="ck_model_registry_provider_key"),
        CheckConstraint("length(model_key) BETWEEN 1 AND 128", name="ck_model_registry_model_key"),
        CheckConstraint("length(model_version) BETWEEN 1 AND 128", name="ck_model_registry_model_version"),
        CheckConstraint("endpoint_class IN ('ollama_generate', 'openai_compatible_chat', 'custom')", name="ck_model_registry_endpoint"),
        CheckConstraint("privacy_classification IN ('unknown', 'public_only', 'private_approved')", name="ck_model_registry_privacy"),
        CheckConstraint("lifecycle_state IN ('registered', 'candidate', 'promoted', 'retired')", name="ck_model_registry_lifecycle"),
        CheckConstraint("evaluation_state IN ('not_evaluated', 'evaluated')", name="ck_model_registry_evaluation"),
        CheckConstraint("promotion_state IN ('not_promoted', 'promoted', 'rolled_back')", name="ck_model_registry_promotion"),
        CheckConstraint("max_context_tokens IS NULL OR max_context_tokens BETWEEN 1 AND 10000000", name="ck_model_registry_context"),
        CheckConstraint("input_cost_microusd_per_million IS NULL OR input_cost_microusd_per_million >= 0", name="ck_model_registry_input_cost"),
        CheckConstraint("output_cost_microusd_per_million IS NULL OR output_cost_microusd_per_million >= 0", name="ck_model_registry_output_cost"),
        Index("ix_model_registry_lifecycle", "lifecycle_state", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint_class: Mapped[str] = mapped_column(String(32), nullable=False)
    privacy_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    max_context_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_cost_microusd_per_million: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_cost_microusd_per_million: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    evaluation_state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_evaluated")
    promotion_state: Mapped[str] = mapped_column(String(32), nullable=False, default="not_promoted")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelTaskCapabilityModel(Base):
    __tablename__ = "model_task_capabilities"
    __table_args__ = (
        UniqueConstraint("model_registry_id", "task_key", "task_version", name="uq_model_task_capability"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_task_capabilities_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_task_capabilities_version"),
        CheckConstraint("capability_state IN ('registered', 'disabled')", name="ck_model_task_capabilities_state"),
        Index("ix_model_task_capabilities_task", "task_key", "task_version"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_registry_id: Mapped[str] = mapped_column(ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    capability_state: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelPromptVersionModel(Base):
    """Immutable code-owned prompt/schema identifiers, never rendered prompts."""

    __tablename__ = "model_prompt_versions"
    __table_args__ = (
        UniqueConstraint("task_key", "task_version", "prompt_version", name="uq_model_prompt_task_version"),
        UniqueConstraint("prompt_checksum", name="uq_model_prompt_checksum"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_prompt_versions_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_prompt_versions_task_version"),
        CheckConstraint("length(prompt_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_prompt_version"),
        CheckConstraint("length(output_schema_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_schema_version"),
        CheckConstraint("length(safety_policy_version) BETWEEN 1 AND 64", name="ck_model_prompt_versions_safety_version"),
        CheckConstraint("length(prompt_checksum) = 64", name="ck_model_prompt_versions_checksum"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    output_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    safety_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelRunProvenanceModel(Base):
    """Bounded immutable record for one logical report-synthesis execution."""

    __tablename__ = "model_run_provenance"
    __table_args__ = (
        UniqueConstraint("report_id", "task_key", "task_version", name="uq_model_run_report_task"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_run_provenance_task_key"),
        CheckConstraint("scope_class IN ('public', 'private', 'organization', 'anonymous')", name="ck_model_run_provenance_scope"),
        CheckConstraint("outcome IN ('disabled', 'provider_unavailable', 'succeeded', 'validation_fallback', 'provider_failure')", name="ck_model_run_provenance_outcome"),
        CheckConstraint("validation_result IN ('not_run', 'accepted', 'invalid_json', 'schema_invalid', 'unsafe_output', 'provider_error', 'policy_denied')", name="ck_model_run_provenance_validation"),
        CheckConstraint("fallback_reason IS NULL OR length(fallback_reason) BETWEEN 1 AND 64", name="ck_model_run_provenance_fallback"),
        CheckConstraint("length(deterministic_input_checksum) = 64", name="ck_model_run_provenance_input_checksum"),
        CheckConstraint("retrieval_digest IS NULL OR length(retrieval_digest) = 64", name="ck_model_run_provenance_retrieval_digest"),
        CheckConstraint("retrieval_source_count BETWEEN 0 AND 64", name="ck_model_run_provenance_retrieval_count"),
        CheckConstraint("latency_ms IS NULL OR latency_ms BETWEEN 0 AND 3600000", name="ck_model_run_provenance_latency"),
        CheckConstraint("input_tokens IS NULL OR input_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_output_tokens"),
        CheckConstraint("total_tokens IS NULL OR total_tokens BETWEEN 0 AND 10000000", name="ck_model_run_provenance_total_tokens"),
        CheckConstraint("cost_microusd IS NULL OR cost_microusd >= 0", name="ck_model_run_provenance_cost"),
        Index("ix_model_run_provenance_owner_created", "owner_user_id", "created_at"),
        Index("ix_model_run_provenance_org_created", "organization_id", "created_at"),
        Index("ix_model_run_provenance_anonymous", "anonymous_session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("model_prompt_versions.id", ondelete="RESTRICT"), nullable=False)
    model_registry_id: Mapped[str | None] = mapped_column(ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=True)
    route_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_route_versions.id", ondelete="RESTRICT"), nullable=True)
    evaluation_run_id: Mapped[str | None] = mapped_column(ForeignKey("model_evaluation_runs.id", ondelete="RESTRICT"), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    anonymous_session_id: Mapped[str | None] = mapped_column(ForeignKey("anonymous_sessions.id", ondelete="SET NULL"), nullable=True)
    scope_class: Mapped[str] = mapped_column(String(16), nullable=False)
    deterministic_input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retrieval_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_result: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelEvaluationDatasetModel(Base):
    """Immutable identity for checked-in public or synthetic evaluation cases."""

    __tablename__ = "model_evaluation_datasets"
    __table_args__ = (
        UniqueConstraint("task_key", "task_version", "dataset_version", name="uq_model_evaluation_dataset_version"),
        UniqueConstraint("dataset_checksum", name="uq_model_evaluation_dataset_checksum"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_evaluation_datasets_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_evaluation_datasets_task_version"),
        CheckConstraint("length(dataset_version) BETWEEN 1 AND 64", name="ck_model_evaluation_datasets_version"),
        CheckConstraint("length(purpose) BETWEEN 1 AND 128", name="ck_model_evaluation_datasets_purpose"),
        CheckConstraint("length(dataset_checksum) = 64", name="ck_model_evaluation_datasets_checksum"),
        CheckConstraint("case_count BETWEEN 1 AND 1000", name="ck_model_evaluation_datasets_case_count"),
        CheckConstraint("lifecycle_state IN ('active', 'retired')", name="ck_model_evaluation_datasets_lifecycle"),
        Index("ix_model_evaluation_datasets_task", "task_key", "task_version", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelEvaluationRunModel(Base):
    """Bounded durable evidence for one candidate against a versioned dataset."""

    __tablename__ = "model_evaluation_runs"
    __table_args__ = (
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_evaluation_runs_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_evaluation_runs_task_version"),
        CheckConstraint("environment IN ('development', 'test', 'staging', 'production', 'portfolio_demo', 'exercise')", name="ck_model_evaluation_runs_environment"),
        CheckConstraint("baseline_type IN ('deterministic_fallback', 'promoted_route')", name="ck_model_evaluation_runs_baseline"),
        CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_model_evaluation_runs_status"),
        CheckConstraint("length(policy_version) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_policy_version"),
        CheckConstraint("length(policy_checksum) = 64", name="ck_model_evaluation_runs_policy_checksum"),
        CheckConstraint("length(code_revision) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_code_revision"),
        CheckConstraint("case_count BETWEEN 0 AND 1000", name="ck_model_evaluation_runs_case_count"),
        CheckConstraint("passed_case_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_passed_count"),
        CheckConstraint("structured_output_valid_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_structure_count"),
        CheckConstraint("deterministic_preserved_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_deterministic_count"),
        CheckConstraint("source_integrity_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_source_count"),
        CheckConstraint("missing_data_honesty_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_missing_count"),
        CheckConstraint("unsafe_language_violation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_unsafe_count"),
        CheckConstraint("privacy_policy_violation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_privacy_count"),
        CheckConstraint("provider_failure_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_provider_failure_count"),
        CheckConstraint("latency_known_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_latency_count"),
        CheckConstraint("latency_total_ms >= 0", name="ck_model_evaluation_runs_latency_total"),
        CheckConstraint("token_observation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_token_count"),
        CheckConstraint("input_tokens_total >= 0 AND output_tokens_total >= 0 AND total_tokens_total >= 0", name="ck_model_evaluation_runs_token_totals"),
        CheckConstraint("cost_observation_count BETWEEN 0 AND case_count", name="ck_model_evaluation_runs_cost_count"),
        CheckConstraint("cost_microusd_total >= 0", name="ck_model_evaluation_runs_cost_total"),
        CheckConstraint("failure_reason IS NULL OR length(failure_reason) BETWEEN 1 AND 64", name="ck_model_evaluation_runs_failure_reason"),
        Index("ix_model_evaluation_runs_candidate", "candidate_model_registry_id", "started_at"),
        Index("ix_model_evaluation_runs_task_status", "task_key", "task_version", "environment", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("model_evaluation_datasets.id", ondelete="RESTRICT"), nullable=False)
    candidate_model_registry_id: Mapped[str] = mapped_column(ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False)
    baseline_type: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_model_registry_id: Mapped[str | None] = mapped_column(ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=True)
    baseline_route_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("model_prompt_versions.id", ondelete="RESTRICT"), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    code_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    structured_output_valid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deterministic_preserved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_integrity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_data_honesty_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsafe_language_violation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    privacy_policy_violation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_known_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_total_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_microusd_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    promotion_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelEvaluationCaseResultModel(Base):
    """Immutable, redacted case-level evidence; fixtures remain checked in."""

    __tablename__ = "model_evaluation_case_results"
    __table_args__ = (
        UniqueConstraint("evaluation_run_id", "case_id", name="uq_model_evaluation_case_result"),
        CheckConstraint("length(case_id) BETWEEN 1 AND 64", name="ck_model_evaluation_case_results_case_id"),
        CheckConstraint("length(case_checksum) = 64", name="ck_model_evaluation_case_results_checksum"),
        CheckConstraint("reason_code IS NULL OR length(reason_code) BETWEEN 1 AND 64", name="ck_model_evaluation_case_results_reason"),
        CheckConstraint("latency_ms IS NULL OR latency_ms BETWEEN 0 AND 3600000", name="ck_model_evaluation_case_results_latency"),
        CheckConstraint("input_tokens IS NULL OR input_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_input_tokens"),
        CheckConstraint("output_tokens IS NULL OR output_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_output_tokens"),
        CheckConstraint("total_tokens IS NULL OR total_tokens BETWEEN 0 AND 10000000", name="ck_model_evaluation_case_results_total_tokens"),
        CheckConstraint("cost_microusd IS NULL OR cost_microusd >= 0", name="ck_model_evaluation_case_results_cost"),
        Index("ix_model_evaluation_case_results_run", "evaluation_run_id", "case_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("model_evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    case_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    structured_output_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deterministic_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_integrity: Mapped[bool] = mapped_column(Boolean, nullable=False)
    missing_data_honesty: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unsafe_language_violation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    privacy_policy_violation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider_failure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelRouteVersionModel(Base):
    """Immutable promoted-route history; active authority lives in the assignment."""

    __tablename__ = "model_route_versions"
    __table_args__ = (
        UniqueConstraint("task_key", "task_version", "environment", "route_version", name="uq_model_route_version"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_route_versions_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_route_versions_task_version"),
        CheckConstraint("environment IN ('development', 'test', 'staging', 'production', 'portfolio_demo', 'exercise')", name="ck_model_route_versions_environment"),
        CheckConstraint("route_version > 0", name="ck_model_route_versions_version"),
        CheckConstraint("route_state IN ('promoted')", name="ck_model_route_versions_state"),
        Index("ix_model_route_versions_task", "task_key", "task_version", "environment", "route_version"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    route_version: Mapped[int] = mapped_column(Integer, nullable=False)
    route_state: Mapped[str] = mapped_column(String(32), nullable=False, default="promoted")
    model_registry_id: Mapped[str] = mapped_column(ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("model_prompt_versions.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("model_evaluation_runs.id", ondelete="RESTRICT"), nullable=False)
    previous_route_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_route_versions.id", ondelete="RESTRICT"), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelRouteAssignmentModel(Base):
    """The one mutable, lockable task/environment runtime authority pointer."""

    __tablename__ = "model_route_assignments"
    __table_args__ = (
        UniqueConstraint("task_key", "task_version", "environment", name="uq_model_route_assignment_scope"),
        CheckConstraint(TASK_KEY_CHECK, name="ck_model_route_assignments_task_key"),
        CheckConstraint("length(task_version) BETWEEN 1 AND 32", name="ck_model_route_assignments_task_version"),
        CheckConstraint("environment IN ('development', 'test', 'staging', 'production', 'portfolio_demo', 'exercise')", name="ck_model_route_assignments_environment"),
        CheckConstraint("assignment_generation >= 0", name="ck_model_route_assignments_generation"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False)
    task_version: Mapped[str] = mapped_column(String(32), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    active_route_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_route_versions.id", ondelete="RESTRICT"), nullable=True)
    assignment_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ModelRouteTransitionModel(Base):
    """Immutable, bounded promotion and rollback history."""

    __tablename__ = "model_route_transitions"
    __table_args__ = (
        CheckConstraint("action IN ('promoted', 'rolled_back')", name="ck_model_route_transitions_action"),
        CheckConstraint("reason_code IS NULL OR length(reason_code) BETWEEN 1 AND 64", name="ck_model_route_transitions_reason"),
        CheckConstraint("assignment_generation >= 0", name="ck_model_route_transitions_generation"),
        Index("ix_model_route_transitions_assignment", "assignment_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("model_route_assignments.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    from_route_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_route_versions.id", ondelete="RESTRICT"), nullable=True)
    to_route_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_route_versions.id", ondelete="RESTRICT"), nullable=True)
    evaluation_run_id: Mapped[str | None] = mapped_column(ForeignKey("model_evaluation_runs.id", ondelete="RESTRICT"), nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignment_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


def _reject_prompt_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model prompt version rows are immutable")


def _reject_model_run_update(_mapper, _connection, target) -> None:
    state = inspect(target)
    changed = {attribute.key for attribute in state.attrs if attribute.history.has_changes()}
    organization_history = state.attrs.organization_id.history
    if changed == {"organization_id"} and organization_history.added == [None]:
        return
    raise ValueError("Model run provenance rows are immutable")


def _reject_model_evaluation_dataset_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model evaluation dataset rows are immutable")


def _reject_completed_model_evaluation_run_update(_mapper, _connection, target) -> None:
    history = inspect(target).attrs.status.history
    previous = history.deleted[0] if history.deleted else (history.unchanged[0] if history.unchanged else None)
    if previous in {"completed", "failed"}:
        raise ValueError("Completed model evaluation runs are immutable")


def _reject_model_evaluation_case_result_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model evaluation case result rows are immutable")


def _reject_model_route_version_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model route version rows are immutable")


def _reject_model_route_transition_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model route transition rows are immutable")


def _reject_governance_evidence_delete(_mapper, _connection, _target) -> None:
    raise ValueError("Model evaluation and route evidence rows are immutable")


event.listen(ModelPromptVersionModel, "before_update", _reject_prompt_update)
event.listen(ModelRunProvenanceModel, "before_update", _reject_model_run_update)
event.listen(ModelEvaluationDatasetModel, "before_update", _reject_model_evaluation_dataset_update)
event.listen(ModelEvaluationRunModel, "before_update", _reject_completed_model_evaluation_run_update)
event.listen(ModelEvaluationCaseResultModel, "before_update", _reject_model_evaluation_case_result_update)
event.listen(ModelRouteVersionModel, "before_update", _reject_model_route_version_update)
event.listen(ModelRouteTransitionModel, "before_update", _reject_model_route_transition_update)
for _immutable_model in (
    ModelEvaluationDatasetModel,
    ModelEvaluationRunModel,
    ModelEvaluationCaseResultModel,
    ModelRouteVersionModel,
    ModelRouteTransitionModel,
):
    event.listen(_immutable_model, "before_delete", _reject_governance_evidence_delete)
