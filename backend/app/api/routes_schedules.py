from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.core.config import get_settings
from app.db.session import get_db
from app.scheduling.schemas import (
    MonitoringScheduleActionResponse,
    MonitoringScheduleCreateRequest,
    MonitoringScheduleRunsResponse,
    MonitoringSchedulesResponse,
)
from app.scheduling.service import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedule_runs,
    list_schedules,
    pause_schedule,
    resume_schedule,
    schedule_response,
)


router = APIRouter(prefix="/schedules", tags=["schedules"])


def require_schedule_owner(actor: UserContext = Depends(require_authenticated_user)) -> UserContext:
    """Reject development demo identities; schedules are never anonymous work."""

    if not get_settings().auth_enabled or not actor.auth_enabled:
        raise HTTPException(status_code=403, detail="Monitoring schedules require enabled authentication.")
    return actor


@router.post("", response_model=MonitoringScheduleActionResponse, status_code=201)
def create_monitoring_schedule(
    request: MonitoringScheduleCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleActionResponse:
    return create_schedule(db, actor, request)


@router.get("", response_model=MonitoringSchedulesResponse)
def read_monitoring_schedules(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringSchedulesResponse:
    return MonitoringSchedulesResponse(
        items=list_schedules(db, actor),
        dispatch_enabled=get_settings().schedule_dispatch_enabled,
    )


@router.get("/{schedule_id}", response_model=MonitoringScheduleActionResponse)
def read_monitoring_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleActionResponse:
    return MonitoringScheduleActionResponse(schedule=schedule_response(get_schedule(db, actor, schedule_id)))


@router.post("/{schedule_id}/pause", response_model=MonitoringScheduleActionResponse)
def pause_monitoring_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleActionResponse:
    return pause_schedule(db, actor, schedule_id)


@router.post("/{schedule_id}/resume", response_model=MonitoringScheduleActionResponse)
def resume_monitoring_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleActionResponse:
    return resume_schedule(db, actor, schedule_id)


@router.delete("/{schedule_id}", response_model=MonitoringScheduleActionResponse)
def delete_monitoring_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleActionResponse:
    return delete_schedule(db, actor, schedule_id)


@router.get("/{schedule_id}/runs", response_model=MonitoringScheduleRunsResponse)
def read_monitoring_schedule_runs(
    schedule_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_schedule_owner),
) -> MonitoringScheduleRunsResponse:
    return MonitoringScheduleRunsResponse(items=list_schedule_runs(db, actor, schedule_id, limit=limit))
