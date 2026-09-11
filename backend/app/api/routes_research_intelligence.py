from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.research_intelligence.schemas import ScenarioComparisonRequest, ScenarioComparisonResponse
from app.research_intelligence.service import compare_scenarios


router = APIRouter(tags=["research-intelligence"])


@router.post("/research/scenarios/compare", response_model=ScenarioComparisonResponse)
def compare_scenarios_route(
    request: ScenarioComparisonRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ScenarioComparisonResponse:
    # Authentication keeps the research surface consistent with saved-thesis work.
    del db, actor
    return compare_scenarios(request)
