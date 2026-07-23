from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.options.analysis import analyze_option
from app.options.schemas import OptionsAnalysisRequest, OptionsAnalysisResponse
from app.quotas.service import ACTION_OPTIONS, consume_quota

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
) -> OptionsAnalysisResponse:
    consume_quota(db, actor, ACTION_OPTIONS)
    return analyze_option(request)
