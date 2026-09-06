"""Server-owned evaluated route resolution for runtime model use."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.llm.governance import ensure_report_synthesis_prompt_version
from app.llm.provenance import ModelIdentity, provider_identity, provider_is_eligible_for_scope
from app.llm.providers import get_llm_provider
from app.llm.task_registry import get_model_task_definition
from app.models.model_governance import (
    ModelEvaluationRunModel,
    ModelRegistryModel,
    ModelRouteAssignmentModel,
    ModelRouteVersionModel,
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


def server_environment(settings: Settings | None = None) -> str:
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
        "exercise": "exercise",
    }.get(configured, "development")


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
    if not _valid_evidence(evaluation, route, prompt.id) or not _valid_model(model, route):
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
    )


def _valid_route(route: ModelRouteVersionModel, task_key: str, task_version: str, environment: str) -> bool:
    return (
        route.task_key == task_key
        and route.task_version == task_version
        and route.environment == environment
        and route.route_state == "promoted"
    )


def _valid_evidence(
    evaluation: ModelEvaluationRunModel | None,
    route: ModelRouteVersionModel,
    prompt_id: str,
) -> bool:
    return bool(
        evaluation
        and evaluation.id == route.evaluation_run_id
        and evaluation.candidate_model_registry_id == route.model_registry_id
        and evaluation.prompt_version_id == prompt_id == route.prompt_version_id
        and evaluation.status == "completed"
        and evaluation.promotion_eligible
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
