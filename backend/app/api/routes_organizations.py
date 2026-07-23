from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.knowledge_base.organization_schemas import (
    OrganizationKnowledgeSourceCreateRequest,
    OrganizationKnowledgeSourceResponse,
    OrganizationKnowledgeSourcesResponse,
)
from app.knowledge_base.organization_service import (
    create_organization_knowledge_source,
    delete_organization_knowledge_source,
    list_organization_knowledge_sources,
)
from app.organizations.schemas import (
    MembershipCreateRequest,
    MembershipResponse,
    MembershipsResponse,
    MembershipUpdateRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationsResponse,
    OrganizationUpdateRequest,
)
from app.organizations.service import (
    add_member,
    create_organization,
    delete_organization,
    get_organization,
    list_members,
    list_organizations,
    remove_member,
    update_member,
    update_organization,
)

router = APIRouter(tags=["organizations"])


@router.get(
    "/organizations/{organization_id}/knowledge-sources",
    response_model=OrganizationKnowledgeSourcesResponse,
)
def get_organization_knowledge_sources(
    organization_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationKnowledgeSourcesResponse:
    return OrganizationKnowledgeSourcesResponse(
        items=list_organization_knowledge_sources(db, actor, organization_id)
    )


@router.post(
    "/organizations/{organization_id}/knowledge-sources",
    response_model=OrganizationKnowledgeSourceResponse,
)
def post_organization_knowledge_source(
    organization_id: str,
    request: OrganizationKnowledgeSourceCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationKnowledgeSourceResponse:
    return create_organization_knowledge_source(db, actor, organization_id, request)


@router.delete(
    "/organizations/{organization_id}/knowledge-sources/{source_id}",
    response_model=OrganizationKnowledgeSourceResponse,
)
def delete_organization_knowledge_source_route(
    organization_id: str,
    source_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationKnowledgeSourceResponse:
    return delete_organization_knowledge_source(db, actor, organization_id, source_id)


@router.get("/organizations", response_model=OrganizationsResponse)
def get_organizations(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationsResponse:
    return OrganizationsResponse(items=list_organizations(db, actor))


@router.post("/organizations", response_model=OrganizationResponse)
def post_organization(
    request: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationResponse:
    return create_organization(db, actor, request)


@router.get("/organizations/{organization_id}", response_model=OrganizationResponse)
def get_organization_route(
    organization_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationResponse:
    return get_organization(db, actor, organization_id)


@router.patch("/organizations/{organization_id}", response_model=OrganizationResponse)
def patch_organization(
    organization_id: str,
    request: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationResponse:
    return update_organization(db, actor, organization_id, request)


@router.delete("/organizations/{organization_id}", response_model=OrganizationResponse)
def delete_organization_route(
    organization_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationResponse:
    return delete_organization(db, actor, organization_id)


@router.get("/organizations/{organization_id}/members", response_model=MembershipsResponse)
def get_members(
    organization_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MembershipsResponse:
    return MembershipsResponse(items=list_members(db, actor, organization_id))


@router.post("/organizations/{organization_id}/members", response_model=MembershipResponse)
def post_member(
    organization_id: str,
    request: MembershipCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MembershipResponse:
    return add_member(db, actor, organization_id, request)


@router.patch(
    "/organizations/{organization_id}/members/{membership_id}",
    response_model=MembershipResponse,
)
def patch_member(
    organization_id: str,
    membership_id: str,
    request: MembershipUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MembershipResponse:
    return update_member(db, actor, organization_id, membership_id, request)


@router.delete(
    "/organizations/{organization_id}/members/{membership_id}",
    response_model=MembershipResponse,
)
def delete_member(
    organization_id: str,
    membership_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MembershipResponse:
    return remove_member(db, actor, organization_id, membership_id)
