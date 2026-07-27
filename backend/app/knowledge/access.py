from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.auth.policies import MANAGE_ORG_ROLES, READ_ORG_ROLES, has_org_role
from app.auth.schemas import UserContext
from app.models.knowledge import KnowledgeSourceModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel


KnowledgeVisibility = Literal["public", "private", "organization"]


@dataclass(frozen=True)
class KnowledgeAccessScope:
    user_id: str
    organization_ids: frozenset[str]
    include_public: bool = True


def derive_knowledge_access_scope(db: Session, actor: UserContext) -> KnowledgeAccessScope:
    organization_ids = frozenset(
        db.execute(
            select(OrganizationMembershipModel.organization_id)
            .join(
                OrganizationModel,
                OrganizationModel.id == OrganizationMembershipModel.organization_id,
            )
            .where(OrganizationMembershipModel.user_id == actor.id)
            .where(OrganizationMembershipModel.status == "active")
            .where(OrganizationModel.status == "active")
            .where(OrganizationModel.deleted_at.is_(None))
        ).scalars()
    )
    return KnowledgeAccessScope(user_id=actor.id, organization_ids=organization_ids)


def create_knowledge_source(
    db: Session,
    actor: UserContext,
    *,
    visibility: KnowledgeVisibility,
    title: str,
    source_type: str,
    organization_id: str | None = None,
    source_uri: str | None = None,
    canonical_uri: str | None = None,
    protocol: str | None = None,
    chain: str | None = None,
) -> KnowledgeSourceModel:
    owner_user_id, authorized_organization_id = _derive_creation_scope(
        db,
        actor,
        visibility,
        organization_id,
    )
    normalized_title = title.strip()
    normalized_source_type = source_type.strip().lower()
    if not normalized_title or len(normalized_title) > 255:
        raise HTTPException(status_code=422, detail="Knowledge source title is invalid")
    if not normalized_source_type or len(normalized_source_type) > 64:
        raise HTTPException(status_code=422, detail="Knowledge source type is invalid")

    now = datetime.now(UTC)
    source = KnowledgeSourceModel(
        id=f"ksrc_{uuid4().hex[:12]}",
        owner_user_id=owner_user_id,
        organization_id=authorized_organization_id,
        visibility=visibility,
        source_type=normalized_source_type,
        source_uri=_optional_trimmed(source_uri, 2048, "source_uri"),
        canonical_uri=_optional_trimmed(canonical_uri, 2048, "canonical_uri"),
        title=normalized_title,
        protocol=_optional_trimmed(protocol, 64, "protocol", lowercase=True),
        chain=_optional_trimmed(chain, 64, "chain", lowercase=True),
        status="registered",
        trust_state="needs_review",
        created_by_user_id=actor.id,
        created_at=now,
        updated_at=now,
    )
    db.add(source)
    db.flush()
    return source


def list_visible_knowledge_sources(
    db: Session,
    actor: UserContext,
) -> list[KnowledgeSourceModel]:
    return db.execute(
        visible_knowledge_sources_statement(db, actor).order_by(
            KnowledgeSourceModel.created_at.desc(),
            KnowledgeSourceModel.id.desc(),
        )
    ).scalars().all()


def get_visible_knowledge_source(
    db: Session,
    actor: UserContext,
    source_id: str,
) -> KnowledgeSourceModel:
    source = db.execute(
        visible_knowledge_sources_statement(db, actor).where(
            KnowledgeSourceModel.id == source_id
        )
    ).scalars().first()
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return source


def visible_knowledge_sources_statement(
    db: Session,
    actor: UserContext,
) -> Select[tuple[KnowledgeSourceModel]]:
    scope = derive_knowledge_access_scope(db, actor)
    public_filter = and_(
        KnowledgeSourceModel.visibility == "public",
        or_(
            KnowledgeSourceModel.trust_state == "approved_for_rag",
            actor.is_admin,
        ),
    )
    private_filter = and_(
        KnowledgeSourceModel.visibility == "private",
        KnowledgeSourceModel.owner_user_id == scope.user_id,
    )
    organization_filter = and_(
        KnowledgeSourceModel.visibility == "organization",
        KnowledgeSourceModel.organization_id.in_(scope.organization_ids),
    )
    return (
        select(KnowledgeSourceModel)
        .where(KnowledgeSourceModel.deleted_at.is_(None))
        .where(KnowledgeSourceModel.status != "deleted")
        .where(or_(public_filter, private_filter, organization_filter))
    )


def trusted_knowledge_sources_statement(
    db: Session,
    actor: UserContext,
) -> Select[tuple[KnowledgeSourceModel]]:
    return (
        visible_knowledge_sources_statement(db, actor)
        .where(KnowledgeSourceModel.trust_state == "approved_for_rag")
        .where(KnowledgeSourceModel.status == "ingested")
    )


def can_manage_knowledge_source(
    db: Session,
    actor: UserContext,
    source: KnowledgeSourceModel,
) -> bool:
    if source.deleted_at is not None or source.status == "deleted":
        return False
    if source.visibility == "public":
        return actor.is_admin
    if source.visibility == "private":
        return source.owner_user_id == actor.id
    if source.visibility == "organization" and source.organization_id:
        return has_org_role(db, actor.id, source.organization_id, MANAGE_ORG_ROLES)
    return False


def _derive_creation_scope(
    db: Session,
    actor: UserContext,
    visibility: KnowledgeVisibility,
    organization_id: str | None,
) -> tuple[str | None, str | None]:
    if visibility == "public":
        if organization_id is not None or not actor.is_admin:
            raise HTTPException(status_code=403, detail="Platform administrator role required")
        return None, None
    if visibility == "private":
        if organization_id is not None:
            raise HTTPException(status_code=422, detail="Private sources cannot select an organization")
        return actor.id, None
    if visibility != "organization" or not organization_id:
        raise HTTPException(status_code=422, detail="Organization source scope is invalid")
    if has_org_role(db, actor.id, organization_id, MANAGE_ORG_ROLES):
        return actor.id, organization_id
    status_code = (
        403
        if has_org_role(db, actor.id, organization_id, READ_ORG_ROLES)
        else 404
    )
    raise HTTPException(
        status_code=status_code,
        detail="Organization owner/admin role required" if status_code == 403 else "Organization not found",
    )


def _optional_trimmed(
    value: str | None,
    maximum: int,
    field_name: str,
    *,
    lowercase: bool = False,
) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise HTTPException(status_code=422, detail=f"Knowledge source {field_name} is invalid")
    return normalized.lower() if lowercase else normalized
