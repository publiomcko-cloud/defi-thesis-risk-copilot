from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.jobs.access import get_visible_job
from app.jobs.control_service import (
    cancel_job,
    job_response,
    list_job_events,
    list_visible_jobs,
    replay_job,
    submit_job,
)
from app.jobs.schemas import JobEventsResponse, JobResponse, JobsResponse, JobSubmissionRequest, JobSubmissionResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobSubmissionResponse, status_code=202)
def create_job(
    request: JobSubmissionRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JobSubmissionResponse:
    job, replayed = submit_job(db, actor, request, idempotency_key)
    return JobSubmissionResponse(job=job_response(job), idempotent_replay=replayed)


@router.get("", response_model=JobsResponse)
def read_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> JobsResponse:
    return JobsResponse(items=[job_response(job) for job in list_visible_jobs(db, actor, limit)])


@router.get("/{job_id}", response_model=JobResponse)
def read_job(
    job_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> JobResponse:
    return job_response(get_visible_job(db, actor, job_id))


@router.post("/{job_id}/cancel", response_model=JobResponse)
def request_cancellation(
    job_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> JobResponse:
    return job_response(cancel_job(db, actor, job_id))


@router.get("/{job_id}/events", response_model=JobEventsResponse)
def read_job_events(
    job_id: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> JobEventsResponse:
    return list_job_events(db, actor, job_id, after_sequence, limit)


@router.post("/{job_id}/replay", response_model=JobResponse, status_code=202)
def create_replay(
    job_id: str,
    db: Session = Depends(get_db),
    operator: UserContext = Depends(require_admin),
) -> JobResponse:
    return job_response(replay_job(db, operator, job_id))
