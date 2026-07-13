from fastapi import APIRouter

from app.options.analysis import analyze_option
from app.options.schemas import OptionsAnalysisRequest, OptionsAnalysisResponse

router = APIRouter(tags=["options"])


@router.post("/options/analyze", response_model=OptionsAnalysisResponse)
def analyze_options(request: OptionsAnalysisRequest) -> OptionsAnalysisResponse:
    return analyze_option(request)
