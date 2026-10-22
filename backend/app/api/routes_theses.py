from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.research_copilot.service import (
    get_thesis_research_run,
    list_thesis_research_runs,
    start_thesis_research,
)
from app.schemas.research import ResearchQuestionRequest, ResearchRunSummary, ResearchRunsResponse
from app.theses.schemas import ThesisCreateRequest, ThesisResponse, ThesesResponse, ThesisUpdateRequest
from app.theses.service import create_thesis, delete_thesis, get_thesis, list_theses, update_thesis
from app.research_intelligence.schemas import (
    CatalystCreateRequest,
    CatalystResponse,
    CatalystUpdateRequest,
    CatalystsResponse,
    MonitoringQuestionsResponse,
    ResearchAssumptionCreateRequest,
    ResearchAssumptionResponse,
    ResearchAssumptionUpdateRequest,
    ResearchAssumptionsResponse,
    ThesisHistoryResponse,
    ThesisRevisionResponse,
    ThesisStatusUpdateRequest,
)
from app.research_intelligence.service import (
    create_assumption,
    create_catalyst,
    list_assumptions,
    list_catalysts,
    list_history,
    monitoring_questions,
    update_assumption,
    update_catalyst,
    update_status,
)

router = APIRouter(tags=["theses"])


@router.get("/theses", response_model=ThesesResponse)
def get_theses(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesesResponse:
    return ThesesResponse(items=list_theses(db, actor))


@router.post("/theses", response_model=ThesisResponse)
def post_thesis(
    request: ThesisCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return create_thesis(db, actor, request)


@router.get("/theses/{thesis_id}", response_model=ThesisResponse)
def get_thesis_route(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return get_thesis(db, actor, thesis_id)


@router.post(
    "/theses/{thesis_id}/research",
    response_model=ResearchRunSummary,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def post_thesis_research(
    thesis_id: str,
    request: ResearchQuestionRequest,
    response: Response,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ResearchRunSummary:
    result = start_thesis_research(db, actor, thesis_id, request, idempotency_key)
    if result.status == "running":
        response.status_code = 202
    return result


@router.get("/theses/{thesis_id}/research-runs", response_model=ResearchRunsResponse)
def get_thesis_research_runs(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ResearchRunsResponse:
    return list_thesis_research_runs(db, actor, thesis_id)


@router.get("/theses/{thesis_id}/research-runs/{run_id}", response_model=ResearchRunSummary)
def get_thesis_research_run_route(
    thesis_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ResearchRunSummary:
    return get_thesis_research_run(db, actor, thesis_id, run_id)


@router.get("/theses/{thesis_id}/history", response_model=ThesisHistoryResponse)
def get_thesis_history(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisHistoryResponse:
    return list_history(db, actor, thesis_id)


@router.post("/theses/{thesis_id}/status", response_model=ThesisRevisionResponse)
def post_thesis_status(
    thesis_id: str,
    request: ThesisStatusUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisRevisionResponse:
    return update_status(db, actor, thesis_id, request)


@router.get("/theses/{thesis_id}/assumptions", response_model=ResearchAssumptionsResponse)
def get_thesis_assumptions(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ResearchAssumptionsResponse:
    return ResearchAssumptionsResponse(items=list_assumptions(db, actor, thesis_id))


@router.post("/theses/{thesis_id}/assumptions", response_model=ResearchAssumptionResponse)
def post_thesis_assumption(
    thesis_id: str,
    request: ResearchAssumptionCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ResearchAssumptionResponse:
    return create_assumption(db, actor, thesis_id, request)


@router.patch("/theses/{thesis_id}/assumptions/{assumption_id}", response_model=ResearchAssumptionResponse)
def patch_thesis_assumption(
    thesis_id: str,
    assumption_id: str,
    request: ResearchAssumptionUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ResearchAssumptionResponse:
    return update_assumption(db, actor, thesis_id, assumption_id, request)


@router.get("/theses/{thesis_id}/catalysts", response_model=CatalystsResponse)
def get_thesis_catalysts(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CatalystsResponse:
    return CatalystsResponse(items=list_catalysts(db, actor, thesis_id))


@router.post("/theses/{thesis_id}/catalysts", response_model=CatalystResponse)
def post_thesis_catalyst(
    thesis_id: str,
    request: CatalystCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CatalystResponse:
    return create_catalyst(db, actor, thesis_id, request)


@router.patch("/theses/{thesis_id}/catalysts/{catalyst_id}", response_model=CatalystResponse)
def patch_thesis_catalyst(
    thesis_id: str,
    catalyst_id: str,
    request: CatalystUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CatalystResponse:
    return update_catalyst(db, actor, thesis_id, catalyst_id, request)


@router.get("/theses/{thesis_id}/monitoring-questions", response_model=MonitoringQuestionsResponse)
def get_monitoring_questions(
    thesis_id: str,
    report_id: str | None = Query(default=None, min_length=1, max_length=64),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> MonitoringQuestionsResponse:
    return monitoring_questions(db, actor, thesis_id, report_id)


@router.patch("/theses/{thesis_id}", response_model=ThesisResponse)
def patch_thesis(
    thesis_id: str,
    request: ThesisUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return update_thesis(db, actor, thesis_id, request)


@router.delete("/theses/{thesis_id}", response_model=ThesisResponse)
def delete_thesis_route(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return delete_thesis(db, actor, thesis_id)
