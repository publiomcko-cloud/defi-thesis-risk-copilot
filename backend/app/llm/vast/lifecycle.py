import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import Settings, get_settings
from app.llm.base import LLMRequest
from app.llm.vast.client import VastClient, VastClientError, select_offer
from app.llm.vast.provider import VastEphemeralProvider
from app.llm.vast.schemas import (
    ACTIVE_STATUSES,
    VastCleanupResponse,
    VastConfigResponse,
    VastSessionResponse,
    VastTestPromptResponse,
)
from app.llm.vast.templates import build_test_prompt
from app.models.vast_session import VastSessionModel
from app.providers.credential_service import get_enabled_credential_secret


def vast_config_response(settings: Settings | None = None) -> VastConfigResponse:
    settings = settings or get_settings()
    return VastConfigResponse(
        enabled=settings.vast_enabled,
        dry_run=settings.vast_dry_run,
        api_base_url=settings.vast_api_base_url,
        credential_name=settings.vast_credential_name,
        has_env_api_key=bool(settings.vast_api_key),
        max_hourly_cost_usd=settings.vast_max_hourly_cost_usd,
        max_session_minutes=settings.vast_max_session_minutes,
        max_active_instances=settings.vast_max_active_instances,
        gpu_allowlist=_gpu_allowlist(settings),
        min_gpu_ram_gb=settings.vast_min_gpu_ram_gb,
        disk_gb=settings.vast_disk_gb,
        require_verified=settings.vast_require_verified,
        auto_destroy=settings.vast_auto_destroy,
        idle_timeout_seconds=settings.vast_idle_timeout_seconds,
        image=settings.vast_image,
        model=settings.vast_model,
        container_port=settings.vast_container_port,
        startup_timeout_seconds=settings.vast_startup_timeout_seconds,
        poll_interval_seconds=settings.vast_poll_interval_seconds,
        job_enabled=settings.vast_job_enabled,
    )


def start_session(
    db: Session,
    actor: UserContext,
    allow_remote_gpu: bool = False,
    warm_instance: bool = False,
    client: VastClient | None = None,
    *,
    session_id: str | None = None,
    source_job_id: str | None = None,
) -> VastSessionModel:
    settings = get_settings()
    if not settings.vast_enabled:
        raise HTTPException(status_code=400, detail="Vast.ai provider is disabled")
    if not settings.vast_dry_run and not allow_remote_gpu:
        raise HTTPException(status_code=400, detail="Remote GPU use must be explicitly allowed")

    if session_id:
        existing = db.get(VastSessionModel, session_id)
        if existing is not None:
            if existing.source_job_id != source_job_id:
                raise HTTPException(status_code=409, detail="Vast session is linked to another job")
            # A retry after a lost completion response must reconcile this durable
            # provider request rather than submit another rental.
            return existing
    if _active_session_count(db) >= settings.vast_max_active_instances:
        raise HTTPException(status_code=409, detail="Vast.ai max active instance limit reached")

    session = VastSessionModel(
        id=session_id or f"vast_{uuid4().hex[:12]}",
        status="idle",
        provider="vast_ai",
        source_job_id=source_job_id,
        model=settings.vast_model or "dry-run-model",
        image=settings.vast_image or "dry-run-image",
        max_runtime_minutes=settings.vast_max_session_minutes,
        container_port=settings.vast_container_port,
        created_by=actor.id,
        metadata_json={
            "dry_run": settings.vast_dry_run,
            "warm_instance": warm_instance,
            "auto_destroy": settings.vast_auto_destroy,
            "provider_profile": "environment_v1",
        },
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    record_audit_event(db, actor.id, "vast.session_start_requested", "vast_session", session.id)

    vast_client = client or _client_from_config(db, settings)
    try:
        _transition(db, session, "searching_offer")
        offers = vast_client.search_offers()
        offer = select_offer(offers, settings)
        if offer is None:
            _fail(db, actor, session, "offer_not_found", "No acceptable Vast.ai offer found")
            return session
        session.offer_id = offer.id
        session.gpu_name = offer.gpu_name
        session.hourly_cost_usd = offer.hourly_cost_usd
        _merge_metadata(session, {"selected_offer": offer.model_dump(exclude={"metadata"})})
        db.commit()
        record_audit_event(
            db,
            actor.id,
            "vast.offer_selected",
            "vast_session",
            session.id,
            {"offer_id": offer.id, "gpu_name": offer.gpu_name, "hourly_cost_usd": offer.hourly_cost_usd},
        )

        _transition(db, session, "renting_instance")
        rented = vast_client.rent_instance(offer, session.image, session.model, settings.vast_disk_gb)
        session.vast_instance_id = str(rented.get("instance_id") or "")
        session.vast_contract_id = str(rented.get("contract_id") or "")
        session.public_endpoint_url = rented.get("public_endpoint_url") or offer.public_endpoint_url
        _merge_metadata(session, {"rent": _safe_metadata(rented)})
        db.commit()
        record_audit_event(db, actor.id, "vast.instance_rented", "vast_session", session.id)

        status = _wait_for_instance_ready(db, actor, session, vast_client, settings)
        if session.status in {"destroyed", "cleanup_failed"}:
            return session
        _merge_metadata(session, {"instance_status": _safe_metadata(status)})
        session.public_endpoint_url = status.get("public_endpoint_url") or session.public_endpoint_url
        db.commit()

        _transition(db, session, "starting_model_server")
        _transition(db, session, "health_checking")
        session.health_status = str(status.get("health_status") or status.get("status") or "healthy")
        if not _is_ready_status(status):
            _fail(db, actor, session, "model_health_failed", "Model health check failed")
            _attempt_cleanup(db, actor, session, vast_client)
            return session
        session.status = "ready"
        session.ready_at = datetime.now(UTC)
        db.commit()
        db.refresh(session)
        record_audit_event(db, actor.id, "vast.model_health_ready", "vast_session", session.id)
        return session
    except VastClientError as exc:
        _fail(db, actor, session, "rent_failed", str(exc))
        _attempt_cleanup(db, actor, session, vast_client)
        return session
    except Exception as exc:
        _fail(db, actor, session, "request_failed", "Vast.ai startup failed")
        _attempt_cleanup(db, actor, session, vast_client)
        _merge_metadata(session, {"startup_exception": exc.__class__.__name__})
        db.commit()
        return session


def list_sessions(db: Session) -> list[VastSessionModel]:
    return db.execute(select(VastSessionModel).order_by(VastSessionModel.created_at.desc())).scalars().all()


def get_session_or_404(db: Session, session_id: str) -> VastSessionModel:
    session = db.get(VastSessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Vast.ai session not found")
    return session


def run_test_prompt(
    db: Session,
    actor: UserContext,
    session_id: str,
    prompt: str,
) -> VastTestPromptResponse:
    settings = get_settings()
    session = get_session_or_404(db, session_id)
    if session.status != "ready":
        raise HTTPException(status_code=409, detail="Vast.ai session is not ready")
    _transition(db, session, "serving_request")
    try:
        provider = VastEphemeralProvider(session, dry_run=settings.vast_dry_run)
        response = provider.generate(
            LLMRequest(
                prompt=build_test_prompt(prompt),
                timeout_seconds=float(settings.llm_timeout_seconds),
            )
        )
        session.last_used_at = datetime.now(UTC)
        session.status = "ready"
        db.commit()
        db.refresh(session)
        record_audit_event(db, actor.id, "vast.test_prompt_run", "vast_session", session.id)
        if settings.vast_auto_destroy and not session.metadata_json.get("warm_instance"):
            session = destroy_session(db, actor, session.id)
        return VastTestPromptResponse(
            session=session_response(session),
            output=response.text,
            provider=response.provider,
            model=response.model,
        )
    except Exception:
        _fail(db, actor, session, "request_failed", "Vast.ai test prompt failed")
        if settings.vast_auto_destroy:
            destroy_session(db, actor, session.id)
        raise


def destroy_session(
    db: Session,
    actor: UserContext,
    session_id: str,
    client: VastClient | None = None,
) -> VastSessionModel:
    settings = get_settings()
    session = get_session_or_404(db, session_id)
    if session.status == "destroyed":
        return session
    record_audit_event(db, actor.id, "vast.destroy_requested", "vast_session", session.id)
    _attempt_cleanup(db, actor, session, client or _client_from_config(db, settings))
    return session


def cleanup_sessions(db: Session, actor: UserContext) -> VastCleanupResponse:
    settings = get_settings()
    now = datetime.now(UTC)
    sessions = db.execute(
        select(VastSessionModel).where(VastSessionModel.status.in_(list(ACTIVE_STATUSES)))
    ).scalars().all()
    cleaned: list[VastSessionModel] = []
    failed_count = 0
    client = _client_from_config(db, settings)
    for session in sessions:
        created_at = _aware_datetime(session.created_at)
        last_used_at = _aware_datetime(session.last_used_at) if session.last_used_at else None
        runtime_expired = created_at + timedelta(minutes=session.max_runtime_minutes) <= now
        idle_expired = bool(
            last_used_at
            and last_used_at + timedelta(seconds=settings.vast_idle_timeout_seconds) <= now
        )
        should_clean = runtime_expired or idle_expired or session.status != "ready"
        if not should_clean:
            continue
        before = session.status
        _attempt_cleanup(db, actor, session, client)
        cleaned.append(session)
        if session.status == "cleanup_failed" and before != "cleanup_failed":
            failed_count += 1
    record_audit_event(
        db,
        actor.id,
        "vast.cleanup_completed",
        "vast_session",
        None,
        {"cleaned_count": len(cleaned), "failed_count": failed_count},
    )
    return VastCleanupResponse(
        cleaned_count=len([item for item in cleaned if item.status == "destroyed"]),
        failed_count=failed_count,
        sessions=[session_response(item) for item in cleaned],
    )


def session_response(session: VastSessionModel) -> VastSessionResponse:
    return VastSessionResponse(
        id=session.id,
        status=session.status,
        provider=session.provider,
        vast_instance_id=session.vast_instance_id,
        vast_contract_id=session.vast_contract_id,
        offer_id=session.offer_id,
        model=session.model,
        image=session.image,
        gpu_name=session.gpu_name,
        hourly_cost_usd=session.hourly_cost_usd,
        max_runtime_minutes=session.max_runtime_minutes,
        container_port=session.container_port,
        public_endpoint_url=session.public_endpoint_url,
        health_status=session.health_status,
        last_error=session.last_error,
        created_by=session.created_by,
        created_at=session.created_at,
        ready_at=session.ready_at,
        last_used_at=session.last_used_at,
        destroyed_at=session.destroyed_at,
        cleanup_attempted_at=session.cleanup_attempted_at,
        metadata_json=session.metadata_json or {},
    )


def _transition(db: Session, session: VastSessionModel, status: str) -> None:
    session.status = status
    db.commit()
    db.refresh(session)


def _fail(
    db: Session,
    actor: UserContext,
    session: VastSessionModel,
    status: str,
    message: str,
) -> None:
    session.status = status
    session.last_error = message
    db.commit()
    db.refresh(session)
    record_audit_event(
        db,
        actor.id,
        "vast.failure_state",
        "vast_session",
        session.id,
        {"status": status, "error": message},
    )


def _attempt_cleanup(
    db: Session,
    actor: UserContext,
    session: VastSessionModel,
    client: VastClient,
) -> None:
    session.status = "cleanup"
    session.cleanup_attempted_at = datetime.now(UTC)
    db.commit()
    try:
        if session.vast_instance_id:
            result = client.destroy_instance(session.vast_instance_id)
            _merge_metadata(session, {"destroy": _safe_metadata(result)})
        session.status = "destroyed"
        session.destroyed_at = datetime.now(UTC)
        db.commit()
        db.refresh(session)
    except Exception:
        session.status = "cleanup_failed"
        session.last_error = "Vast.ai cleanup failed"
        db.commit()
        db.refresh(session)
        record_audit_event(db, actor.id, "vast.failure_state", "vast_session", session.id, {"status": "cleanup_failed"})


def _active_session_count(db: Session) -> int:
    return len(
        db.execute(select(VastSessionModel).where(VastSessionModel.status.in_(list(ACTIVE_STATUSES)))).scalars().all()
    )


def _wait_for_instance_ready(
    db: Session,
    actor: UserContext,
    session: VastSessionModel,
    client: VastClient,
    settings: Settings,
) -> dict:
    _transition(db, session, "booting")
    if settings.vast_dry_run:
        return client.get_instance_status(session.vast_instance_id or "")

    deadline = datetime.now(UTC) + timedelta(seconds=settings.vast_startup_timeout_seconds)
    last_status: dict = {}
    while datetime.now(UTC) <= deadline:
        last_status = client.get_instance_status(session.vast_instance_id or "")
        _merge_metadata(session, {"last_polled_status": _safe_metadata(last_status)})
        session.public_endpoint_url = last_status.get("public_endpoint_url") or session.public_endpoint_url
        session.health_status = str(last_status.get("health_status") or last_status.get("status") or "unknown")
        db.commit()

        if _is_ready_status(last_status):
            return last_status
        if _is_failed_status(last_status):
            _fail(
                db,
                actor,
                session,
                "container_failed",
                f"Vast.ai instance entered unsafe state: {session.health_status}",
            )
            _attempt_cleanup(db, actor, session, client)
            return last_status
        time.sleep(max(settings.vast_poll_interval_seconds, 0))

    _fail(db, actor, session, "boot_timeout", "Vast.ai startup timed out")
    _attempt_cleanup(db, actor, session, client)
    return last_status or {"status": "timeout", "health_status": "timeout"}


def _is_ready_status(status: dict) -> bool:
    state = str(status.get("status") or "").lower()
    health = str(status.get("health_status") or "").lower()
    return state in {"running", "ready"} and health in {"healthy", "ready", "running", ""}


def _is_failed_status(status: dict) -> bool:
    state = str(status.get("status") or status.get("health_status") or "").lower()
    health = str(status.get("health_status") or "").lower()
    failed_values = {"exited", "offline", "unknown", "failed", "error", "stopped", "terminated"}
    return state in failed_values or health in failed_values


def _merge_metadata(session: VastSessionModel, metadata: dict) -> None:
    existing = dict(session.metadata_json or {})
    existing.update(metadata)
    session.metadata_json = existing


def _safe_metadata(metadata: dict) -> dict:
    return {key: value for key, value in metadata.items() if "key" not in key.lower() and "token" not in key.lower()}


def _gpu_allowlist(settings: Settings) -> list[str]:
    return [item.strip() for item in settings.vast_gpu_allowlist.split(",") if item.strip()]


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _client_from_config(db: Session, settings: Settings) -> VastClient:
    credential_secret = get_enabled_credential_secret(
        db,
        provider="vast_ai",
        name=settings.vast_credential_name,
    )
    return VastClient(settings, api_key=credential_secret or settings.vast_api_key)
