from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import AuditEventsResponse, UserContext
from app.auth.service import audit_event_response
from app.core.config import get_settings
from app.db.session import get_db
from app.models.access_audit_event import AccessAuditEventModel
from app.providers.credential_service import (
    create_provider_credential,
    disable_provider_credential,
    list_provider_credentials,
    update_provider_credential,
)
from app.providers.schemas import (
    ProviderCredentialCreateRequest,
    ProviderCredentialResponse,
    ProviderCredentialsResponse,
    ProviderCredentialUpdateRequest,
)
from app.jobs.schemas import (
    JobOperationsResponse,
    WorkerCredentialCreateRequest,
    WorkerCredentialIssuedResponse,
    WorkerCredentialResponse,
    WorkerCredentialRotateRequest,
    WorkerCredentialsResponse,
    WorkerRegistrationRequest,
    WorkerResponse,
    WorkersResponse,
)
from app.jobs.control_service import job_operations_summary
from app.jobs.worker_service import (
    disable_worker,
    issue_worker_credential,
    list_worker_credentials,
    list_workers,
    register_worker,
    revoke_worker_credential,
    rotate_worker_credential,
)

router = APIRouter(tags=["admin"])


@router.post("/admin/provider-credentials", response_model=ProviderCredentialResponse)
def create_credential(
    request: ProviderCredentialCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> ProviderCredentialResponse:
    _block_public_demo_mutation()
    return ProviderCredentialResponse(
        credential=create_provider_credential(request, db, current_user)
    )


@router.get("/admin/provider-credentials", response_model=ProviderCredentialsResponse)
def get_credentials(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> ProviderCredentialsResponse:
    return ProviderCredentialsResponse(items=list_provider_credentials(db))


@router.patch("/admin/provider-credentials/{credential_id}", response_model=ProviderCredentialResponse)
def patch_credential(
    credential_id: str,
    request: ProviderCredentialUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> ProviderCredentialResponse:
    _block_public_demo_mutation()
    return ProviderCredentialResponse(
        credential=update_provider_credential(credential_id, request, db, current_user)
    )


@router.delete("/admin/provider-credentials/{credential_id}", response_model=ProviderCredentialResponse)
def delete_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> ProviderCredentialResponse:
    _block_public_demo_mutation()
    return ProviderCredentialResponse(
        credential=disable_provider_credential(credential_id, db, current_user)
    )


@router.get("/admin/audit-events", response_model=AuditEventsResponse)
def get_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> AuditEventsResponse:
    records = db.execute(
        select(AccessAuditEventModel).order_by(AccessAuditEventModel.created_at.desc()).limit(limit)
    ).scalars().all()
    return AuditEventsResponse(items=[audit_event_response(record) for record in records])


@router.post("/admin/workers", response_model=WorkerResponse)
def create_worker(
    request: WorkerRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> WorkerResponse:
    _block_public_demo_mutation()
    return register_worker(db, current_user, request)


@router.get("/admin/workers", response_model=WorkersResponse)
def get_workers(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> WorkersResponse:
    return WorkersResponse(items=list_workers(db))


@router.get("/admin/jobs/operations", response_model=JobOperationsResponse)
def get_job_operations(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> JobOperationsResponse:
    return job_operations_summary(db)


@router.post("/admin/workers/{worker_id}/disable", response_model=WorkerResponse)
def disable_registered_worker(
    worker_id: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> WorkerResponse:
    _block_public_demo_mutation()
    return disable_worker(db, current_user, worker_id)


@router.post("/admin/workers/{worker_id}/credentials", response_model=WorkerCredentialIssuedResponse)
def create_worker_credential(
    worker_id: str,
    request: WorkerCredentialCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> WorkerCredentialIssuedResponse:
    _block_public_demo_mutation()
    return issue_worker_credential(db, current_user, worker_id, request)


@router.get("/admin/workers/{worker_id}/credentials", response_model=WorkerCredentialsResponse)
def get_worker_credentials(
    worker_id: str,
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> WorkerCredentialsResponse:
    return WorkerCredentialsResponse(items=list_worker_credentials(db, worker_id))


@router.post(
    "/admin/worker-credentials/{credential_id}/rotate",
    response_model=WorkerCredentialIssuedResponse,
)
def rotate_registered_worker_credential(
    credential_id: str,
    request: WorkerCredentialRotateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> WorkerCredentialIssuedResponse:
    _block_public_demo_mutation()
    return rotate_worker_credential(
        db,
        current_user,
        credential_id,
        request,
        revoke_previous=request.revoke_previous,
    )


@router.post("/admin/worker-credentials/{credential_id}/revoke", response_model=WorkerCredentialResponse)
def revoke_registered_worker_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> WorkerCredentialResponse:
    _block_public_demo_mutation()
    return revoke_worker_credential(db, current_user, credential_id)


def _block_public_demo_mutation() -> None:
    settings = get_settings()
    if settings.public_demo_mode and not settings.auth_enabled:
        raise HTTPException(
            status_code=403,
            detail="Provider credential changes are disabled in public demo mode.",
        )
