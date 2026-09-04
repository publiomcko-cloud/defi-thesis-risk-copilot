"""Durable model-governance persistence for the Phase 21A report path."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.llm.prompts import report_synthesis_prompt_definition
from app.llm.provenance import ModelIdentity, ModelRunCandidate
from app.llm.task_registry import get_model_task_definition
from app.models.model_governance import (
    ModelPromptVersionModel,
    ModelRegistryModel,
    ModelRunProvenanceModel,
    ModelTaskCapabilityModel,
)


REPORT_SYNTHESIS_PROMPT_ID = "prompt_report_synthesis_v1"


class ModelGovernanceConflict(ValueError):
    """Raised when durable code-owned governance facts do not match source."""


def ensure_report_synthesis_prompt_version(db: Session) -> ModelPromptVersionModel:
    """Materialize the code-owned prompt version without ever storing its text."""

    definition = report_synthesis_prompt_definition()
    existing = db.get(ModelPromptVersionModel, REPORT_SYNTHESIS_PROMPT_ID)
    if existing is not None:
        _assert_prompt_matches_source(existing)
        return existing

    candidate = ModelPromptVersionModel(
        id=REPORT_SYNTHESIS_PROMPT_ID,
        task_key=definition.task_key,
        task_version=definition.task_version,
        prompt_version=definition.prompt_version,
        output_schema_version=definition.output_schema_version,
        safety_policy_version=definition.safety_policy_version,
        prompt_checksum=definition.checksum,
        created_at=datetime.now(UTC),
    )
    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
        return candidate
    except IntegrityError:
        existing = db.get(ModelPromptVersionModel, REPORT_SYNTHESIS_PROMPT_ID)
        if existing is None:
            raise
        _assert_prompt_matches_source(existing)
        return existing


def ensure_configured_model_registration(
    db: Session,
    identity: ModelIdentity,
) -> ModelRegistryModel:
    """Register a configured model idempotently; registration never promotes it."""

    task = get_model_task_definition("report_synthesis")
    model_id = _stable_id(
        "model",
        identity.provider_key,
        identity.model_key,
        identity.model_version,
        identity.endpoint_class,
    )
    existing = db.get(ModelRegistryModel, model_id)
    if existing is None:
        candidate = ModelRegistryModel(
            id=model_id,
            provider_key=identity.provider_key,
            model_key=identity.model_key,
            model_version=identity.model_version,
            endpoint_class=identity.endpoint_class,
            privacy_classification=identity.privacy_classification,
            lifecycle_state="registered",
            evaluation_state="not_evaluated",
            promotion_state="not_promoted",
            created_at=datetime.now(UTC),
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            existing = candidate
        except IntegrityError:
            existing = db.get(ModelRegistryModel, model_id)
            if existing is None:
                raise
    _assert_model_matches_identity(existing, identity)
    _ensure_task_capability(db, existing, task.key, task.version)
    return existing


def record_model_run_provenance(
    db: Session,
    *,
    report_id: str,
    candidate: ModelRunCandidate,
    owner_user_id: str | None,
    organization_id: str | None,
    anonymous_session_id: str | None,
) -> ModelRunProvenanceModel:
    """Insert one immutable run record in the report transaction or return it.

    ``uq_model_run_report_task`` is the final retry/recovery authority. No
    provider adapter writes here, so a report rollback also removes its run row.
    """

    task = get_model_task_definition(candidate.task_key)
    if candidate.task_version != task.version:
        raise ModelGovernanceConflict("Model task version does not match the code-owned registry")
    prompt = ensure_report_synthesis_prompt_version(db)
    _assert_candidate_prompt_linkage(candidate, prompt)
    model = ensure_configured_model_registration(db, candidate.provider) if candidate.provider else None
    existing = db.execute(
        select(ModelRunProvenanceModel)
        .where(ModelRunProvenanceModel.report_id == report_id)
        .where(ModelRunProvenanceModel.task_key == candidate.task_key)
        .where(ModelRunProvenanceModel.task_version == candidate.task_version)
    ).scalars().one_or_none()
    if existing is not None:
        return existing

    record = ModelRunProvenanceModel(
        id=_stable_id("modelrun", report_id, candidate.task_key, candidate.task_version),
        report_id=report_id,
        task_key=candidate.task_key,
        task_version=candidate.task_version,
        prompt_version_id=prompt.id,
        model_registry_id=model.id if model else None,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        anonymous_session_id=anonymous_session_id,
        scope_class=candidate.scope_class,
        deterministic_input_checksum=candidate.deterministic_input_checksum,
        retrieval_digest=candidate.retrieval_digest,
        retrieval_source_count=candidate.retrieval_source_count,
        validation_result=candidate.validation_result,
        outcome=candidate.outcome,
        fallback_reason=candidate.fallback_reason,
        latency_ms=candidate.latency_ms,
        input_tokens=candidate.input_tokens,
        output_tokens=candidate.output_tokens,
        total_tokens=candidate.total_tokens,
        cost_microusd=candidate.cost_microusd,
        created_at=datetime.now(UTC),
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
        return record
    except IntegrityError:
        existing = db.execute(
            select(ModelRunProvenanceModel)
            .where(ModelRunProvenanceModel.report_id == report_id)
            .where(ModelRunProvenanceModel.task_key == candidate.task_key)
            .where(ModelRunProvenanceModel.task_version == candidate.task_version)
        ).scalars().one_or_none()
        if existing is None:
            raise
        return existing


def disabled_report_synthesis_candidate(candidate: ModelRunCandidate) -> ModelRunCandidate:
    """Discard a stale worker model claim when the server-side kill switch is off."""

    return replace(
        candidate,
        provider=None,
        outcome="disabled",
        validation_result="not_run",
        fallback_reason="synthesis_disabled",
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        cost_microusd=None,
    )


def export_model_run_provenance(db: Session, owner_user_id: str) -> list[dict]:
    rows = db.execute(
        select(ModelRunProvenanceModel)
        .where(ModelRunProvenanceModel.owner_user_id == owner_user_id)
        .order_by(ModelRunProvenanceModel.created_at, ModelRunProvenanceModel.id)
    ).scalars().all()
    return [
        {
            "report_id": row.report_id,
            "task_key": row.task_key,
            "task_version": row.task_version,
            "prompt_version_id": row.prompt_version_id,
            "model_registry_id": row.model_registry_id,
            "organization_id": row.organization_id,
            "scope_class": row.scope_class,
            "deterministic_input_checksum": row.deterministic_input_checksum,
            "retrieval_digest": row.retrieval_digest,
            "retrieval_source_count": row.retrieval_source_count,
            "validation_result": row.validation_result,
            "outcome": row.outcome,
            "fallback_reason": row.fallback_reason,
            "latency_ms": row.latency_ms,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens,
            "cost_microusd": row.cost_microusd,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def dispose_model_runs_for_account(db: Session, owner_user_id: str) -> int:
    """Remove owner-linked model metadata with the existing account deletion path."""

    return db.execute(
        delete(ModelRunProvenanceModel).where(ModelRunProvenanceModel.owner_user_id == owner_user_id)
    ).rowcount or 0


def clear_model_run_organization_context(
    db: Session,
    organization_id: str,
) -> int:
    """Keep bounded provenance while removing a deleted organization context."""

    return db.execute(
        update(ModelRunProvenanceModel)
        .where(ModelRunProvenanceModel.organization_id == organization_id)
        .values(organization_id=None)
    ).rowcount or 0


def remove_model_runs_for_expired_reports(db: Session, report_ids: list[str]) -> int:
    if not report_ids:
        return 0
    return db.execute(
        delete(ModelRunProvenanceModel).where(ModelRunProvenanceModel.report_id.in_(report_ids))
    ).rowcount or 0


def _ensure_task_capability(
    db: Session,
    model: ModelRegistryModel,
    task_key: str,
    task_version: str,
) -> ModelTaskCapabilityModel:
    capability_id = _stable_id("modelcap", model.id, task_key, task_version)
    existing = db.get(ModelTaskCapabilityModel, capability_id)
    if existing is not None:
        return existing
    candidate = ModelTaskCapabilityModel(
        id=capability_id,
        model_registry_id=model.id,
        task_key=task_key,
        task_version=task_version,
        capability_state="registered",
        created_at=datetime.now(UTC),
    )
    try:
        with db.begin_nested():
            db.add(candidate)
            db.flush()
        return candidate
    except IntegrityError:
        existing = db.get(ModelTaskCapabilityModel, capability_id)
        if existing is None:
            raise
        return existing


def _assert_prompt_matches_source(record: ModelPromptVersionModel) -> None:
    definition = report_synthesis_prompt_definition()
    expected = {
        "task_key": definition.task_key,
        "task_version": definition.task_version,
        "prompt_version": definition.prompt_version,
        "output_schema_version": definition.output_schema_version,
        "safety_policy_version": definition.safety_policy_version,
        "prompt_checksum": definition.checksum,
    }
    if any(getattr(record, key) != value for key, value in expected.items()):
        raise ModelGovernanceConflict("Prompt version is immutable; create a new prompt version")


def _assert_model_matches_identity(record: ModelRegistryModel, identity: ModelIdentity) -> None:
    expected = {
        "provider_key": identity.provider_key,
        "model_key": identity.model_key,
        "model_version": identity.model_version,
        "endpoint_class": identity.endpoint_class,
    }
    if any(getattr(record, key) != value for key, value in expected.items()):
        raise ModelGovernanceConflict("Model registry identity is invalid")


def _assert_candidate_prompt_linkage(candidate: ModelRunCandidate, prompt: ModelPromptVersionModel) -> None:
    expected = {
        "task_key": prompt.task_key,
        "task_version": prompt.task_version,
        "prompt_version": prompt.prompt_version,
        "output_schema_version": prompt.output_schema_version,
        "safety_policy_version": prompt.safety_policy_version,
        "prompt_checksum": prompt.prompt_checksum,
    }
    if any(getattr(candidate, key) != value for key, value in expected.items()):
        raise ModelGovernanceConflict("Model run provenance does not match the code-owned prompt version")


def _stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode()
    return f"{prefix}_{sha256(material).hexdigest()[:40]}"
