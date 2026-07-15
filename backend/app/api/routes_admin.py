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


def _block_public_demo_mutation() -> None:
    if get_settings().public_demo_mode:
        raise HTTPException(
            status_code=403,
            detail="Provider credential changes are disabled in public demo mode.",
        )
