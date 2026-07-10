from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import analyze_strategy

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    return analyze_strategy(request, db)
