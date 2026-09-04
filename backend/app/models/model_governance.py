from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event, inspect
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


def _reject_prompt_update(_mapper, _connection, _target) -> None:
    raise ValueError("Model prompt version rows are immutable")


def _reject_model_run_update(_mapper, _connection, target) -> None:
    state = inspect(target)
    changed = {attribute.key for attribute in state.attrs if attribute.history.has_changes()}
    organization_history = state.attrs.organization_id.history
    if changed == {"organization_id"} and organization_history.added == [None]:
        return
    raise ValueError("Model run provenance rows are immutable")


event.listen(ModelPromptVersionModel, "before_update", _reject_prompt_update)
event.listen(ModelRunProvenanceModel, "before_update", _reject_model_run_update)
