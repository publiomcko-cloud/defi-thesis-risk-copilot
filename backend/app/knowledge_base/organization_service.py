from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.policies import MANAGE_ORG_ROLES, READ_ORG_ROLES, has_org_role
from app.auth.schemas import UserContext
from app.knowledge_base.organization_schemas import (
    OrganizationKnowledgeSourceCreateRequest,
    OrganizationKnowledgeSourceResponse,
)
from app.models.organization_knowledge_source import OrganizationKnowledgeSourceModel


def create_organization_knowledge_source(
    db: Session,
    actor: UserContext,
    organization_id: str,
    request: OrganizationKnowledgeSourceCreateRequest,
) -> OrganizationKnowledgeSourceResponse:
    _require_org_role(db, actor, organization_id, MANAGE_ORG_ROLES, manage=True)
    now = datetime.now(UTC)
    source_url = str(request.source_url)
    record = OrganizationKnowledgeSourceModel(
        id=f"oks_{uuid4().hex[:12]}",
        organization_id=organization_id,
        created_by_user_id=actor.id,
        approved_by_user_id=actor.id,
        title=request.title.strip(),
        protocol=request.protocol.strip().lower(),
        source_type=request.source_type.strip().lower(),
        source_url=source_url,
        provenance_hash=_provenance_hash(
            organization_id,
            source_url,
            request.title,
            request.protocol,
            request.source_type,
        ),
        approval_status="approved",
        approval_notes=request.approval_notes.strip() if request.approval_notes else None,
        storage_status="metadata_only",
        status="active",
        approved_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This source URL is already registered for the organization",
        ) from None
    db.refresh(record)
    return organization_knowledge_source_response(record)


def list_organization_knowledge_sources(
    db: Session,
    actor: UserContext,
    organization_id: str,
) -> list[OrganizationKnowledgeSourceResponse]:
    _require_org_role(db, actor, organization_id, READ_ORG_ROLES)
    records = db.execute(
        select(OrganizationKnowledgeSourceModel)
        .where(OrganizationKnowledgeSourceModel.organization_id == organization_id)
        .where(OrganizationKnowledgeSourceModel.deleted_at.is_(None))
        .order_by(OrganizationKnowledgeSourceModel.created_at.desc())
    ).scalars().all()
    return [organization_knowledge_source_response(record) for record in records]


def delete_organization_knowledge_source(
    db: Session,
    actor: UserContext,
    organization_id: str,
    source_id: str,
) -> OrganizationKnowledgeSourceResponse:
    _require_org_role(db, actor, organization_id, MANAGE_ORG_ROLES, manage=True)
    record = db.execute(
        select(OrganizationKnowledgeSourceModel)
        .where(OrganizationKnowledgeSourceModel.id == source_id)
        .where(OrganizationKnowledgeSourceModel.organization_id == organization_id)
        .where(OrganizationKnowledgeSourceModel.deleted_at.is_(None))
    ).scalars().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Organization knowledge source not found")
    record.status = "disabled"
    record.deleted_at = datetime.now(UTC)
    record.updated_at = record.deleted_at
    db.commit()
    db.refresh(record)
    return organization_knowledge_source_response(record)


def organization_knowledge_source_response(
    record: OrganizationKnowledgeSourceModel,
) -> OrganizationKnowledgeSourceResponse:
    return OrganizationKnowledgeSourceResponse(
        id=record.id,
        organization_id=record.organization_id,
        title=record.title,
        protocol=record.protocol,
        source_type=record.source_type,
        source_url=record.source_url,
        provenance_hash=record.provenance_hash,
        approval_status=record.approval_status,
        approval_notes=record.approval_notes,
        storage_status=record.storage_status,
        status=record.status,
        approved_by_user_id=record.approved_by_user_id,
        approved_at=record.approved_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _require_org_role(
    db: Session,
    actor: UserContext,
    organization_id: str,
    roles: set[str],
    manage: bool = False,
) -> None:
    if has_org_role(db, actor.id, organization_id, roles):
        return
    detail = "Organization owner/admin role required" if manage else "Organization not found"
    status_code = 403 if manage and has_org_role(db, actor.id, organization_id, READ_ORG_ROLES) else 404
    raise HTTPException(status_code=status_code, detail=detail)


def _provenance_hash(
    organization_id: str,
    source_url: str,
    title: str,
    protocol: str,
    source_type: str,
) -> str:
    canonical = "\n".join(
        (
            organization_id,
            source_url.strip(),
            title.strip(),
            protocol.strip().lower(),
            source_type.strip().lower(),
        )
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
