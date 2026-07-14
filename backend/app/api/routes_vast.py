from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.db.session import get_db
from app.llm.vast.lifecycle import (
    cleanup_sessions,
    destroy_session,
    get_session_or_404,
    list_sessions,
    run_test_prompt,
    session_response,
    start_session,
    vast_config_response,
)
from app.llm.vast.schemas import (
    VastCleanupResponse,
    VastConfigResponse,
    VastConfigUpdateRequest,
    VastSessionActionResponse,
    VastSessionListResponse,
    VastStartSessionRequest,
    VastTestPromptRequest,
    VastTestPromptResponse,
)

router = APIRouter(tags=["vast"])


@router.get("/admin/vast/config", response_model=VastConfigResponse)
def get_vast_config(_: UserContext = Depends(require_admin)) -> VastConfigResponse:
    return vast_config_response()


@router.post("/admin/vast/config", response_model=VastConfigResponse)
def update_vast_config(
    request: VastConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> VastConfigResponse:
    record_audit_event(
        db,
        current_user.id,
        "vast.config_changed",
        "vast_config",
        None,
        {"note": request.note, "source": "environment-backed"},
    )
    return vast_config_response()


@router.post("/admin/vast/sessions/start", response_model=VastSessionActionResponse)
def start_vast_session(
    request: VastStartSessionRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> VastSessionActionResponse:
    session = start_session(
        db,
        current_user,
        model=request.model,
        image=request.image,
        allow_remote_gpu=request.allow_remote_gpu,
        warm_instance=request.warm_instance,
    )
    return VastSessionActionResponse(session=session_response(session))


@router.get("/admin/vast/sessions", response_model=VastSessionListResponse)
def get_vast_sessions(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> VastSessionListResponse:
    return VastSessionListResponse(items=[session_response(item) for item in list_sessions(db)])


@router.get("/admin/vast/sessions/{session_id}", response_model=VastSessionActionResponse)
def get_vast_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> VastSessionActionResponse:
    return VastSessionActionResponse(session=session_response(get_session_or_404(db, session_id)))


@router.post("/admin/vast/sessions/{session_id}/test-prompt", response_model=VastTestPromptResponse)
def test_vast_prompt(
    session_id: str,
    request: VastTestPromptRequest,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> VastTestPromptResponse:
    return run_test_prompt(db, current_user, session_id, request.prompt)


@router.post("/admin/vast/sessions/{session_id}/destroy", response_model=VastSessionActionResponse)
def destroy_vast_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> VastSessionActionResponse:
    return VastSessionActionResponse(session=session_response(destroy_session(db, current_user, session_id)))


@router.post("/admin/vast/cleanup", response_model=VastCleanupResponse)
def cleanup_vast_sessions(
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> VastCleanupResponse:
    return cleanup_sessions(db, current_user)
