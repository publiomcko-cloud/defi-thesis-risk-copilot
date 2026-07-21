from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.models.organization import OrganizationMembershipModel, OrganizationModel


PUBLIC_KNOWLEDGE_SCOPE = "public_curated"
ORGANIZATION_KNOWLEDGE_SCOPE = "organization"


@dataclass(frozen=True)
class RetrievalScope:
    visible_organization_ids: frozenset[str] = frozenset()
    tenant_storage_enabled: bool = False

    def allows(self, metadata: dict) -> bool:
        knowledge_scope = str(metadata.get("knowledge_scope") or PUBLIC_KNOWLEDGE_SCOPE)
        if knowledge_scope == PUBLIC_KNOWLEDGE_SCOPE:
            return True
        if knowledge_scope != ORGANIZATION_KNOWLEDGE_SCOPE or not self.tenant_storage_enabled:
            return False
        organization_id = metadata.get("organization_id")
        return isinstance(organization_id, str) and organization_id in self.visible_organization_ids


def derive_retrieval_scope(db: Session, actor: UserContext | None) -> RetrievalScope:
    if actor is None or actor.anonymous_session_id:
        return RetrievalScope()
    organization_ids = db.execute(
        select(OrganizationMembershipModel.organization_id)
        .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.organization_id)
        .where(OrganizationMembershipModel.user_id == actor.id)
        .where(OrganizationMembershipModel.status == "active")
        .where(OrganizationModel.status == "active")
        .where(OrganizationModel.deleted_at.is_(None))
    ).scalars().all()
    return RetrievalScope(
        visible_organization_ids=frozenset(organization_ids),
        tenant_storage_enabled=False,
    )
