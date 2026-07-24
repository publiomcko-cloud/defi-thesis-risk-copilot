from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import user_context
from app.db.session import SessionLocal
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.llm.vast.lifecycle import destroy_session, start_session
from app.models.user import UserModel
from app.models.vast_session import VastSessionModel


class VastExecutionError(JobExecutionError):
    """A Vast job cannot safely start or reconcile a provider session."""


class VastJobExecutor:
    """Start one server-profiled Vast session and reconcile retries by source job."""

    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        starter: Callable[..., object] = start_session,
    ) -> None:
        self._session_factory = session_factory
        self._starter = starter

    def execute(self, job: WorkerClaimedJob) -> JobResultEnvelope:
        allow_remote_gpu, warm_instance, session_id, owner_id = _vast_input(job)
        with self._session_factory() as db:
            owner = db.get(UserModel, owner_id)
            if owner is None:
                raise VastExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "vast_owner_unavailable", "Vast job owner is unavailable.")
            try:
                session = self._starter(
                    db,
                    user_context(owner),
                    allow_remote_gpu=allow_remote_gpu,
                    warm_instance=warm_instance,
                    session_id=session_id,
                    source_job_id=job.id,
                )
            except HTTPException as exc:
                raise VastExecutionError(JobErrorCategory.PERMANENT_INPUT, "vast_request_rejected", str(exc.detail)) from exc
            if session.status != "ready":
                category = (
                    JobErrorCategory.UNCERTAIN_EXTERNAL_SIDE_EFFECT
                    if session.provider_request_state in {"submitted_unknown", "reconciliation_failed"}
                    else JobErrorCategory.RETRYABLE_PROVIDER
                )
                raise VastExecutionError(category, "vast_session_not_ready", session.last_error or "Vast session did not reach ready state.")
            return JobResultEnvelope(
                result_schema_version="vast.session.start.v1",
                result_json={
                    "vast_session_id": session.id,
                    "provider_status": session.status,
                    "hourly_cost_microusd": _hourly_cost_microusd(session.hourly_cost_usd),
                },
            )

    def cancel(self, job: WorkerClaimedJob) -> None:
        _, _, session_id, owner_id = _vast_input(job)
        with self._session_factory() as db:
            owner = db.get(UserModel, owner_id)
            if owner is None or db.get(VastSessionModel, session_id) is None:
                return
            try:
                destroy_session(db, user_context(owner), session_id)
            except Exception:
                return


def _vast_input(job: WorkerClaimedJob) -> tuple[bool, bool, str, str]:
    try:
        payload = job.input_json["request"]
        context = job.input_json["_server_context"]
        allow_remote_gpu = payload["allow_remote_gpu"]
        warm_instance = payload["warm_instance"]
        session_id = context["vast_session_id"]
        owner_id = context["owner_user_id"]
    except (KeyError, TypeError) as exc:
        raise VastExecutionError(JobErrorCategory.PERMANENT_INPUT, "vast_input_invalid", "Vast job input is invalid.") from exc
    if not (
        isinstance(allow_remote_gpu, bool)
        and isinstance(warm_instance, bool)
        and isinstance(session_id, str)
        and session_id.startswith("vast_")
        and isinstance(owner_id, str)
        and owner_id
    ):
        raise VastExecutionError(JobErrorCategory.PERMANENT_INPUT, "vast_input_invalid", "Vast job input is invalid.")
    return allow_remote_gpu, warm_instance, session_id, owner_id


def _hourly_cost_microusd(hourly_cost_usd: float | None) -> int:
    return int(round((hourly_cost_usd or 0) * 1_000_000))
