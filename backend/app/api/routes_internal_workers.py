from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.jobs.schemas import (
    WorkerCancellationResponse,
    WorkerClaimRequest,
    WorkerClaimResponse,
    WorkerCompletionRequest,
    WorkerFailureRequest,
    WorkerHeartbeatRequest,
    WorkerLeaseRequest,
    WorkerMutationResponse,
    WorkerProgressRequest,
)
from app.jobs.worker_protocol import (
    authenticate_worker,
    cancellation_status,
    claim_next_job,
    complete_job,
    fail_job,
    heartbeat_job,
    release_job,
    report_progress,
    start_job,
)


router = APIRouter(prefix="/internal/workers/v1", tags=["internal-workers"], include_in_schema=False)
worker_bearer = HTTPBearer(auto_error=False)


def _worker_identity(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
    protocol_version: str | None = None,
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Worker authentication failed.")
    return authenticate_worker(db, credentials.credentials, protocol_version)


@router.post("/claim", response_model=WorkerClaimResponse)
def claim(
    request: WorkerClaimRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerClaimResponse:
    return claim_next_job(db, _worker_identity(credentials, db, request.protocol_version))


@router.post("/jobs/{job_id}/start", response_model=WorkerMutationResponse)
def start(
    job_id: str,
    request: WorkerLeaseRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return start_job(db, _worker_identity(credentials, db), job_id, request)


@router.post("/jobs/{job_id}/heartbeat", response_model=WorkerMutationResponse)
def heartbeat(
    job_id: str,
    request: WorkerHeartbeatRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return heartbeat_job(db, _worker_identity(credentials, db), job_id, request)


@router.post("/jobs/{job_id}/progress", response_model=WorkerMutationResponse)
def progress(
    job_id: str,
    request: WorkerProgressRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return report_progress(db, _worker_identity(credentials, db), job_id, request)


@router.post("/jobs/{job_id}/complete", response_model=WorkerMutationResponse)
def complete(
    job_id: str,
    request: WorkerCompletionRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return complete_job(db, _worker_identity(credentials, db), job_id, request, request.result)


@router.post("/jobs/{job_id}/fail", response_model=WorkerMutationResponse)
def fail(
    job_id: str,
    request: WorkerFailureRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return fail_job(db, _worker_identity(credentials, db), job_id, request)


@router.post("/jobs/{job_id}/release", response_model=WorkerMutationResponse)
def release(
    job_id: str,
    request: WorkerLeaseRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerMutationResponse:
    return release_job(db, _worker_identity(credentials, db), job_id, request)


@router.get("/jobs/{job_id}/cancellation", response_model=WorkerCancellationResponse)
def cancellation(
    job_id: str,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(worker_bearer),
) -> WorkerCancellationResponse:
    return cancellation_status(db, _worker_identity(credentials, db), job_id)
