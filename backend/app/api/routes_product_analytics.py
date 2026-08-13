from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.product_analytics.schemas import (
    PrivacyPreferencesResponse,
    PrivacyPreferenceUpdateRequest,
    PrivacyPreferenceUpdateResponse,
)
from app.product_analytics.service import get_privacy_preference, set_privacy_preference


router = APIRouter(tags=["privacy"])


@router.get("/account/privacy-preferences", response_model=PrivacyPreferencesResponse)
def read_privacy_preferences(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> PrivacyPreferencesResponse:
    return PrivacyPreferencesResponse(items=[get_privacy_preference(db, actor)])


@router.patch("/account/privacy-preferences", response_model=PrivacyPreferenceUpdateResponse)
def update_privacy_preference(
    request: PrivacyPreferenceUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PrivacyPreferenceUpdateResponse:
    return set_privacy_preference(
        db,
        actor,
        enabled=request.enabled,
        idempotency_key=idempotency_key,
    )
