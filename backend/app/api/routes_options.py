from fastapi import APIRouter, Depends

from app.core.public_demo import enforce_public_compute_rate_limit
from app.options.analysis import analyze_option
from app.options.schemas import OptionsAnalysisRequest, OptionsAnalysisResponse

router = APIRouter(tags=["options"])


@router.post(
    "/options/analyze",
    response_model=OptionsAnalysisResponse,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def analyze_options(request: OptionsAnalysisRequest) -> OptionsAnalysisResponse:
    return analyze_option(request)
