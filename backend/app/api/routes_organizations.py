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
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationTokenResponse,
    InvitationResponse,
    InvitationsResponse,
    OrganizationCreateRequest,
    OrganizationExportResponse,
    OrganizationResponse,
    OrganizationsResponse,
    OrganizationUpdateRequest,
    OwnershipTransferRequest,
)
from app.organizations.service import (
    add_member,
    accept_invitation,
    create_invitation,
    resend_invitation,
    revoke_invitation,
    create_organization,
    delete_organization,
    export_organization,
    get_organization,
    list_members,
    list_invitations,
    list_organizations,
    remove_member,
    transfer_organization_ownership,
    update_member,
    update_organization,
)

router = APIRouter(tags=["organizations"])

@router.get("/organizations/{organization_id}/invitations", response_model=InvitationsResponse)
def get_invitations(organization_id: str, db: Session = Depends(get_db), actor: UserContext = Depends(require_authenticated_user)) -> InvitationsResponse:
    return InvitationsResponse(items=list_invitations(db, actor, organization_id))

@router.post(
    "/organizations/{organization_id}/invitations",
    response_model=InvitationTokenResponse,
    response_model_exclude_none=True,
)
def post_invitation(organization_id: str, request: InvitationCreateRequest, db: Session = Depends(get_db), actor: UserContext = Depends(require_authenticated_user)) -> InvitationTokenResponse:
    return create_invitation(db, actor, organization_id, request)

@router.post("/organization-invitations/accept", response_model=MembershipResponse)
def post_accept_invitation(request: InvitationAcceptRequest, db: Session = Depends(get_db), actor: UserContext = Depends(require_authenticated_user)) -> MembershipResponse:
    return accept_invitation(db, actor, request)

@router.post(
    "/organizations/{organization_id}/invitations/{invitation_id}/resend",
    response_model=InvitationTokenResponse,
    response_model_exclude_none=True,
)
def post_resend_invitation(organization_id: str, invitation_id: str, db: Session = Depends(get_db), actor: UserContext = Depends(require_authenticated_user)) -> InvitationTokenResponse:
    return resend_invitation(db, actor, organization_id, invitation_id)

@router.post("/organizations/{organization_id}/invitations/{invitation_id}/revoke", response_model=InvitationResponse)
def post_revoke_invitation(organization_id: str, invitation_id: str, db: Session = Depends(get_db), actor: UserContext = Depends(require_authenticated_user)) -> InvitationResponse:
    return revoke_invitation(db, actor, organization_id, invitation_id)


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


@router.get("/organizations/{organization_id}/export", response_model=OrganizationExportResponse)
def get_organization_export(
    organization_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationExportResponse:
    return export_organization(db, actor, organization_id)


@router.patch("/organizations/{organization_id}", response_model=OrganizationResponse)
def patch_organization(
    organization_id: str,
    request: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> OrganizationResponse:
    return update_organization(db, actor, organization_id, request)


@router.post(
    "/organizations/{organization_id}/transfer-ownership",
    response_model=MembershipResponse,
)
def post_transfer_organization_ownership(
    organization_id: str,
    request: OwnershipTransferRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MembershipResponse:
    return transfer_organization_ownership(db, actor, organization_id, request)


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
