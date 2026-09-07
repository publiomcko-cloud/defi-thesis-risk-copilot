"""Server-owned evaluated route resolution for runtime model use."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.llm.governance import ensure_report_synthesis_prompt_version
from app.llm.provenance import ModelIdentity, provider_identity, provider_is_eligible_for_scope
from app.llm.providers import get_llm_provider
from app.llm.task_registry import get_model_task_definition
from app.models.model_governance import (
    ModelEvaluationDatasetModel,
    ModelEvaluationRunModel,
    ModelRegistryModel,
    ModelRouteAssignmentModel,
    ModelRouteVersionModel,
)


SUPPORTED_ROUTE_ENVIRONMENTS = frozenset(
    {"development", "test", "staging", "production", "portfolio_demo", "exercise"}
)


@dataclass(frozen=True)
class RouteResolution:
    provider: object | None
    identity: ModelIdentity | None
    outcome: str
    validation_result: str
    fallback_reason: str | None
    route_version_id: str | None = None
    evaluation_run_id: str | None = None
    environment: str | None = None
    model_registry_id: str | None = None
    prompt_version_id: str | None = None
    prompt_checksum: str | None = None


@dataclass(frozen=True)
class ExecutionRouteSnapshot:
    """Bounded route authority captured by the server when an async job starts."""

    task_key: str
    task_version: str
    environment: str | None
    scope_class: str
    outcome: str
    validation_result: str
    fallback_reason: str | None
    route_version_id: str | None
    evaluation_run_id: str | None
    model_registry_id: str | None
    prompt_version_id: str | None
    prompt_checksum: str | None
    provider: ModelIdentity | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_key": self.task_key,
            "task_version": self.task_version,
            "environment": self.environment,
            "scope_class": self.scope_class,
            "outcome": self.outcome,
            "validation_result": self.validation_result,
            "fallback_reason": self.fallback_reason,
            "route_version_id": self.route_version_id,
            "evaluation_run_id": self.evaluation_run_id,
            "model_registry_id": self.model_registry_id,
            "prompt_version_id": self.prompt_version_id,
            "prompt_checksum": self.prompt_checksum,
            "provider": _identity_payload(self.provider),
        }


def server_environment(settings: Settings | None = None) -> str | None:
    """Map server configuration to the bounded, non-browser route partition."""

    settings = settings or get_settings()
    if settings.public_demo_mode:
        return "portfolio_demo"
    configured = settings.app_env.strip().lower()
    return {
        "development": "development",
        "dev": "development",
        "test": "test",
        "testing": "test",
        "staging": "staging",
        "production": "production",
        "prod": "production",
        "portfolio_demo": "portfolio_demo",
        "exercise": "exercise",
    }.get(configured)


def resolve_report_synthesis_route(
    db: Session,
    *,
    content_scope: str,
    configured_provider: object | None = None,
    settings: Settings | None = None,
) -> RouteResolution:
    """Resolve a route only after every server-owned authority gate succeeds."""

    settings = settings or get_settings()
    if not settings.llm_synthesis_enabled:
        return _fallback("disabled", "not_run", "synthesis_disabled")

    task = get_model_task_definition("report_synthesis")
    environment = server_environment(settings)
    if environment is None:
        return _fallback("provider_unavailable", "not_run", "unsupported_environment")
    assignment = db.execute(
        select(ModelRouteAssignmentModel).where(
            ModelRouteAssignmentModel.task_key == task.key,
            ModelRouteAssignmentModel.task_version == task.version,
            ModelRouteAssignmentModel.environment == environment,
        )
    ).scalar_one_or_none()
    if assignment is None or assignment.active_route_version_id is None:
        return _fallback("provider_unavailable", "not_run", "no_promoted_route")

    route = db.get(ModelRouteVersionModel, assignment.active_route_version_id)
    if route is None or not _valid_route(route, task.key, task.version, environment):
        return _fallback("provider_unavailable", "not_run", "invalid_promoted_route")
    evaluation = db.get(ModelEvaluationRunModel, route.evaluation_run_id)
    model = db.get(ModelRegistryModel, route.model_registry_id)
    prompt = ensure_report_synthesis_prompt_version(db)
    if not _valid_evidence(db, evaluation, route, prompt.id) or not _valid_model(model, route):
        return _fallback("provider_unavailable", "not_run", "invalid_route_evidence")

    provider = configured_provider if configured_provider is not None else get_llm_provider(settings)
    identity = provider_identity(provider) if provider is not None else None
    if identity is None:
        return _fallback("provider_unavailable", "not_run", "provider_unavailable")
    if not _identity_matches_model(identity, model):
        return _fallback("provider_unavailable", "not_run", "configured_provider_mismatch", identity)
    if not provider_is_eligible_for_scope(identity, content_scope):
        return _fallback("provider_unavailable", "policy_denied", "private_provider_not_approved", identity)
    return RouteResolution(
        provider=provider,
        identity=identity,
        outcome="succeeded",
        validation_result="accepted",
        fallback_reason=None,
        route_version_id=route.id,
        evaluation_run_id=evaluation.id,
        environment=environment,
        model_registry_id=model.id,
        prompt_version_id=prompt.id,
        prompt_checksum=prompt.prompt_checksum,
    )


def capture_report_synthesis_execution_route(
    db: Session,
    *,
    content_scope: str,
    configured_provider: object | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Capture current server-owned route authority for one async execution.

    The captured record is deliberately independent of the mutable assignment.
    Promotion and rollback are prospective: they choose later executions, but do
    not relabel an execution that already started under a valid route.
    """

    settings = settings or get_settings()
    task = get_model_task_definition("report_synthesis")
    resolution = resolve_report_synthesis_route(
        db,
        content_scope=content_scope,
        configured_provider=configured_provider,
        settings=settings,
    )
    return ExecutionRouteSnapshot(
        task_key=task.key,
        task_version=task.version,
        environment=resolution.environment or server_environment(settings),
        scope_class=content_scope,
        outcome=resolution.outcome,
        validation_result=resolution.validation_result,
        fallback_reason=resolution.fallback_reason,
        route_version_id=resolution.route_version_id,
        evaluation_run_id=resolution.evaluation_run_id,
        model_registry_id=resolution.model_registry_id,
        prompt_version_id=resolution.prompt_version_id,
        prompt_checksum=resolution.prompt_checksum,
        provider=resolution.identity if resolution.route_version_id is not None else None,
    ).to_payload()


def resolve_report_synthesis_execution_route(
    db: Session,
    *,
    content_scope: str,
    snapshot_payload: object,
    configured_provider: object | None = None,
    settings: Settings | None = None,
) -> RouteResolution:
    """Resolve exactly the immutable route captured at async execution start.

    This intentionally never reads the current assignment. Historical promoted
    routes remain valid evidence after a prospective promotion or rollback.
    """

    settings = settings or get_settings()
    if not settings.llm_synthesis_enabled:
        return _fallback("disabled", "not_run", "synthesis_disabled")
    try:
        snapshot = _snapshot_from_payload(snapshot_payload)
    except ValueError:
        return _fallback("provider_unavailable", "not_run", "execution_route_snapshot_invalid")
    if snapshot.scope_class != content_scope:
        return _fallback("provider_unavailable", "policy_denied", "execution_route_scope_mismatch")
    if snapshot.route_version_id is None:
        return _fallback(
            snapshot.outcome,
            snapshot.validation_result,
            snapshot.fallback_reason or "no_execution_route",
            snapshot.provider,
        )
    if (
        snapshot.environment not in SUPPORTED_ROUTE_ENVIRONMENTS
        or snapshot.evaluation_run_id is None
        or snapshot.model_registry_id is None
        or snapshot.prompt_version_id is None
        or snapshot.prompt_checksum is None
        or snapshot.provider is None
    ):
        return _fallback("provider_unavailable", "not_run", "execution_route_snapshot_invalid")

    task = get_model_task_definition("report_synthesis")
    route = db.get(ModelRouteVersionModel, snapshot.route_version_id)
    evaluation = db.get(ModelEvaluationRunModel, snapshot.evaluation_run_id)
    model = db.get(ModelRegistryModel, snapshot.model_registry_id)
    prompt = ensure_report_synthesis_prompt_version(db)
    if not (
        _valid_route(route, task.key, task.version, snapshot.environment)
        and route.id == snapshot.route_version_id
        and route.evaluation_run_id == snapshot.evaluation_run_id
        and route.model_registry_id == snapshot.model_registry_id
        and route.prompt_version_id == snapshot.prompt_version_id
        and prompt.id == snapshot.prompt_version_id
        and prompt.prompt_checksum == snapshot.prompt_checksum
        and _valid_evidence(db, evaluation, route, prompt.id)
        and _valid_model(model, route)
    ):
        return _fallback("provider_unavailable", "not_run", "invalid_execution_route_evidence")

    provider = configured_provider if configured_provider is not None else get_llm_provider(settings)
    identity = provider_identity(provider) if provider is not None else None
    if identity is None:
        return _fallback("provider_unavailable", "not_run", "provider_unavailable")
    if identity != snapshot.provider or not _identity_matches_model(identity, model):
        return _fallback("provider_unavailable", "not_run", "configured_provider_mismatch", identity)
    if not provider_is_eligible_for_scope(identity, content_scope):
        return _fallback("provider_unavailable", "policy_denied", "private_provider_not_approved", identity)
    return RouteResolution(
        provider=provider,
        identity=identity,
        outcome="succeeded",
        validation_result="accepted",
        fallback_reason=None,
        route_version_id=route.id,
        evaluation_run_id=evaluation.id,
        environment=snapshot.environment,
        model_registry_id=model.id,
        prompt_version_id=prompt.id,
        prompt_checksum=prompt.prompt_checksum,
    )


def _valid_route(route: ModelRouteVersionModel, task_key: str, task_version: str, environment: str) -> bool:
    return (
        route.task_key == task_key
        and route.task_version == task_version
        and route.environment == environment
        and route.route_state == "promoted"
    )


def _valid_evidence(
    db: Session,
    evaluation: ModelEvaluationRunModel | None,
    route: ModelRouteVersionModel,
    prompt_id: str,
) -> bool:
    from app.llm.evaluation_data import report_synthesis_public_dataset

    definition = report_synthesis_public_dataset()
    dataset = db.get(ModelEvaluationDatasetModel, evaluation.dataset_id) if evaluation else None
    return bool(
        evaluation
        and evaluation.id == route.evaluation_run_id
        and evaluation.candidate_model_registry_id == route.model_registry_id
        and evaluation.prompt_version_id == prompt_id == route.prompt_version_id
        and evaluation.status == "completed"
        and evaluation.promotion_eligible
        and dataset
        and dataset.id == definition.dataset_id
        and dataset.task_key == definition.task_key
        and dataset.task_version == definition.task_version
        and dataset.dataset_version == definition.dataset_version
        and dataset.dataset_checksum == definition.checksum
        and dataset.case_count == len(definition.cases)
        and dataset.lifecycle_state == "active"
    )


def _valid_model(model: ModelRegistryModel | None, route: ModelRouteVersionModel) -> bool:
    return bool(
        model
        and model.id == route.model_registry_id
        and model.lifecycle_state != "retired"
        and model.evaluation_state == "evaluated"
    )


def _identity_matches_model(identity: ModelIdentity, model: ModelRegistryModel) -> bool:
    return (
        identity.provider_key == model.provider_key
        and identity.model_key == model.model_key
        and identity.model_version == model.model_version
        and identity.endpoint_class == model.endpoint_class
        and identity.privacy_classification == model.privacy_classification
    )


def _fallback(
    outcome: str,
    validation_result: str,
    reason: str,
    identity: ModelIdentity | None = None,
) -> RouteResolution:
    return RouteResolution(
        provider=None,
        identity=identity,
        outcome=outcome,
        validation_result=validation_result,
        fallback_reason=reason,
    )


def _identity_payload(identity: ModelIdentity | None) -> dict[str, str] | None:
    if identity is None:
        return None
    return {
        "provider_key": identity.provider_key,
        "model_key": identity.model_key,
        "model_version": identity.model_version,
        "endpoint_class": identity.endpoint_class,
        "privacy_classification": identity.privacy_classification,
    }


def _snapshot_from_payload(payload: object) -> ExecutionRouteSnapshot:
    if not isinstance(payload, dict):
        raise ValueError("execution route snapshot is invalid")
    task = get_model_task_definition(_snapshot_text(payload, "task_key", 64))
    if task.key != "report_synthesis" or _snapshot_text(payload, "task_version", 32) != task.version:
        raise ValueError("execution route task is invalid")
    scope_class = _snapshot_text(payload, "scope_class", 16)
    if scope_class not in {"public", "private", "organization", "anonymous"}:
        raise ValueError("execution route scope is invalid")
    environment = payload.get("environment")
    if environment is not None and environment not in SUPPORTED_ROUTE_ENVIRONMENTS:
        raise ValueError("execution route environment is invalid")
    outcome = _snapshot_text(payload, "outcome", 32)
    validation_result = _snapshot_text(payload, "validation_result", 32)
    fallback_reason = _snapshot_optional_text(payload, "fallback_reason", 64)
    route_version_id = _snapshot_optional_text(payload, "route_version_id", 128)
    evaluation_run_id = _snapshot_optional_text(payload, "evaluation_run_id", 128)
    model_registry_id = _snapshot_optional_text(payload, "model_registry_id", 128)
    prompt_version_id = _snapshot_optional_text(payload, "prompt_version_id", 128)
    prompt_checksum = _snapshot_optional_checksum(payload, "prompt_checksum")
    provider_payload = payload.get("provider")
    provider = _snapshot_identity(provider_payload) if provider_payload is not None else None
    route_fields = (route_version_id, evaluation_run_id, model_registry_id, prompt_version_id, prompt_checksum, provider)
    if route_version_id is None and any(value is not None for value in route_fields[1:]):
        raise ValueError("fallback execution route contains authority")
    if route_version_id is not None and any(value is None for value in route_fields[1:]):
        raise ValueError("model execution route is incomplete")
    return ExecutionRouteSnapshot(
        task_key=task.key,
        task_version=task.version,
        environment=environment,
        scope_class=scope_class,
        outcome=outcome,
        validation_result=validation_result,
        fallback_reason=fallback_reason,
        route_version_id=route_version_id,
        evaluation_run_id=evaluation_run_id,
        model_registry_id=model_registry_id,
        prompt_version_id=prompt_version_id,
        prompt_checksum=prompt_checksum,
        provider=provider,
    )


def _snapshot_identity(payload: object) -> ModelIdentity:
    if not isinstance(payload, dict):
        raise ValueError("execution route provider is invalid")
    provider_key = _snapshot_text(payload, "provider_key", 64)
    model_key = _snapshot_text(payload, "model_key", 128)
    model_version = _snapshot_text(payload, "model_version", 128)
    endpoint_class = _snapshot_text(payload, "endpoint_class", 32)
    privacy_classification = _snapshot_text(payload, "privacy_classification", 32)
    identity = ModelIdentity(provider_key, model_key, model_version, endpoint_class, privacy_classification)
    if provider_identity(_SnapshotProvider(identity)) != identity:
        raise ValueError("execution route provider is invalid")
    return identity


class _SnapshotProvider:
    def __init__(self, identity: ModelIdentity) -> None:
        self.name = identity.provider_key
        self.model = identity.model_key
        self.privacy_classification = identity.privacy_classification


def _snapshot_text(payload: dict[str, Any], key: str, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValueError("execution route text is invalid")
    return value


def _snapshot_optional_text(payload: dict[str, Any], key: str, maximum: int) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    return _snapshot_text(payload, key, maximum)


def _snapshot_optional_checksum(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("execution route checksum is invalid")
    return value
