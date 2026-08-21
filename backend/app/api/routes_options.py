import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.options.analysis import analyze_option
from app.options.schemas import OptionsAnalysisRequest, OptionsAnalysisResponse
from app.quotas.service import ACTION_OPTIONS, consume_quota
from app.entitlements.service import emit_usage

router = APIRouter(tags=["options"])


@router.post(
    "/options/analyze",
    response_model=OptionsAnalysisResponse,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def analyze_options(
    request: OptionsAnalysisRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OptionsAnalysisResponse:
    consume_quota(db, actor, ACTION_OPTIONS)
    response = analyze_option(request)
    if actor.auth_enabled and actor.anonymous_session_id is None:
        source_id = hashlib.sha256((idempotency_key or f"request:{uuid4().hex}").encode()).hexdigest()[:48]
        emit_usage(db, owner_user_id=actor.id, unit_key="usage.options.completed.v1", source_type="options", source_id=source_id)
        db.commit()
    return response
