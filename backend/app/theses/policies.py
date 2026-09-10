from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.auth.policies import READ_ORG_ROLES, WRITE_ORG_ROLES, can_read_resource, can_update_resource, has_org_role
from app.auth.schemas import UserContext
from app.models.saved_thesis import SavedThesisModel


def can_read_saved_thesis(db: Session, actor: UserContext, thesis: SavedThesisModel) -> bool:
    """Apply the saved-thesis authority contract without a creator bypass.

    A thesis in organization visibility remains an organization resource even
    though its creator is retained for attribution and private-scope history.
    """

    if _saved_thesis_is_unavailable(thesis):
        return False
    if thesis.visibility == "organization":
        return bool(
            thesis.organization_id
            and has_org_role(db, actor.id, thesis.organization_id, READ_ORG_ROLES)
        )
    return can_read_resource(actor, thesis, db)


def can_update_saved_thesis(db: Session, actor: UserContext, thesis: SavedThesisModel) -> bool:
    """Require current active organization write authority for org theses."""

    if _saved_thesis_is_unavailable(thesis):
        return False
    if thesis.visibility == "organization":
        return bool(
            thesis.organization_id
            and has_org_role(db, actor.id, thesis.organization_id, WRITE_ORG_ROLES)
        )
    return can_update_resource(actor, thesis, db)


def _saved_thesis_is_unavailable(thesis: SavedThesisModel) -> bool:
    if thesis.deleted_at is not None:
        return True
    expires_at = thesis.expires_at
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)
