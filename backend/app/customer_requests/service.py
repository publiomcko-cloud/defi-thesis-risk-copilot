from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.customer_requests.schemas import (
    CustomerRequestCreateRequest,
    CustomerRequestResponse,
)
from app.models.customer_request import CustomerRequestModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel


PRIVACY_REQUEST_TYPES = frozenset({"privacy_access_export", "privacy_deletion"})


def create_customer_request(
    db: Session,
    actor: UserContext,
    request: CustomerRequestCreateRequest,
) -> CustomerRequestResponse:
    organization_id = _authorized_organization_context(db, actor.id, request.organization_id)
    if request.request_type in PRIVACY_REQUEST_TYPES and organization_id is not None:
        raise HTTPException(status_code=422, detail="Privacy requests cannot include organization context")

    now = datetime.now(UTC)
    record = CustomerRequestModel(
        id=f"creq_{uuid4().hex[:12]}",
        owner_user_id=actor.id,
        organization_id=organization_id,
        request_type=request.request_type,
        subject=request.subject,
        description=request.description,
        workflow_state="open",
        verification_state="authenticated" if request.request_type in PRIVACY_REQUEST_TYPES else "not_required",
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    record_audit_event(
        db,
        actor.id,
        "customer_request.created",
        "customer_request",
        record.id,
        {"request_type": record.request_type, "organization_id": record.organization_id},
        commit=False,
    )
    db.commit()
    db.refresh(record)
    return customer_request_response(record)


def list_customer_requests(db: Session, actor: UserContext) -> list[CustomerRequestResponse]:
    records = db.execute(
        select(CustomerRequestModel)
        .where(CustomerRequestModel.owner_user_id == actor.id)
        .order_by(CustomerRequestModel.created_at.desc(), CustomerRequestModel.id.desc())
    ).scalars().all()
    return [customer_request_response(record) for record in records]


def get_customer_request(
    db: Session,
    actor: UserContext,
    request_id: str,
) -> CustomerRequestResponse:
    return customer_request_response(_owned_customer_request(db, actor.id, request_id))


def close_customer_request(
    db: Session,
    actor: UserContext,
    request_id: str,
) -> CustomerRequestResponse:
    record = db.execute(
        select(CustomerRequestModel)
        .where(CustomerRequestModel.id == request_id)
        .where(CustomerRequestModel.owner_user_id == actor.id)
        .with_for_update()
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Customer request not found")
    if record.workflow_state == "closed":
        return customer_request_response(record)

    now = datetime.now(UTC)
    record.workflow_state = "closed"
    record.resolution_code = "requester_closed"
    record.closed_at = now
    record.updated_at = now
    record_audit_event(
        db,
        actor.id,
        "customer_request.closed",
        "customer_request",
        record.id,
        {"request_type": record.request_type, "workflow_state": "closed"},
        commit=False,
    )
    db.commit()
    db.refresh(record)
    return customer_request_response(record)


def export_customer_requests(db: Session, owner_user_id: str) -> list[dict]:
    records = db.execute(
        select(CustomerRequestModel)
        .where(CustomerRequestModel.owner_user_id == owner_user_id)
        .order_by(CustomerRequestModel.created_at, CustomerRequestModel.id)
    ).scalars().all()
    return [
        {
            "id": record.id,
            "request_type": record.request_type,
            "subject": record.subject,
            "description": record.description,
            "organization_id": record.organization_id,
            "workflow_state": record.workflow_state,
            "verification_state": record.verification_state,
            "resolution_code": record.resolution_code,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "closed_at": record.closed_at,
        }
        for record in records
    ]


def dispose_customer_requests_for_account(db: Session, owner_user_id: str) -> int:
    """Remove private request text during the existing account-deletion transaction."""

    return db.execute(
        delete(CustomerRequestModel).where(CustomerRequestModel.owner_user_id == owner_user_id)
    ).rowcount or 0


def clear_customer_request_organization_context(
    db: Session,
    organization_id: str,
    *,
    now: datetime,
) -> int:
    """Preserve owner-only requests while removing retired organization context."""

    return db.execute(
        update(CustomerRequestModel)
        .where(CustomerRequestModel.organization_id == organization_id)
        .values(organization_id=None, updated_at=now)
    ).rowcount or 0


def customer_request_response(record: CustomerRequestModel) -> CustomerRequestResponse:
    return CustomerRequestResponse(
        id=record.id,
        request_type=record.request_type,
        subject=record.subject,
        description=record.description,
        organization_id=record.organization_id,
        workflow_state=record.workflow_state,
        verification_state=record.verification_state,
        resolution_code=record.resolution_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
        closed_at=record.closed_at,
    )


def _owned_customer_request(
    db: Session,
    owner_user_id: str,
    request_id: str,
) -> CustomerRequestModel:
    record = db.execute(
        select(CustomerRequestModel)
        .where(CustomerRequestModel.id == request_id)
        .where(CustomerRequestModel.owner_user_id == owner_user_id)
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Customer request not found")
    return record


def _authorized_organization_context(
    db: Session,
    owner_user_id: str,
    organization_id: str | None,
) -> str | None:
    if organization_id is None:
        return None
    organization = db.execute(
        select(OrganizationModel)
        .join(
            OrganizationMembershipModel,
            OrganizationMembershipModel.organization_id == OrganizationModel.id,
        )
        .where(OrganizationModel.id == organization_id)
        .where(OrganizationModel.status == "active")
        .where(OrganizationModel.deleted_at.is_(None))
        .where(OrganizationMembershipModel.user_id == owner_user_id)
        .where(OrganizationMembershipModel.status == "active")
    ).scalars().one_or_none()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization.id
