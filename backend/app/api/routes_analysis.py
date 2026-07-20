from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import analyze_strategy

router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def analyze(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> AnalysisResponse:
    return analyze_strategy(request, db, actor)
