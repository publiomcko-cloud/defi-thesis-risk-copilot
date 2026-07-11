from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.monitoring.discovery_service import list_discovered_items, run_monitoring
from app.monitoring.schemas import (
    DiscoveredItemsResponse,
    MonitoringRunRequest,
    MonitoringRunResponse,
)

router = APIRouter(tags=["monitoring"])


@router.post("/monitoring/run", response_model=MonitoringRunResponse)
def run_source_monitoring(
    request: MonitoringRunRequest | None = None,
    db: Session = Depends(get_db),
) -> MonitoringRunResponse:
    return run_monitoring(request or MonitoringRunRequest(), db)


@router.get("/monitoring/discovered-items", response_model=DiscoveredItemsResponse)
def get_discovered_items(
    status: str | None = None,
    protocol: str | None = None,
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> DiscoveredItemsResponse:
    return DiscoveredItemsResponse(
        items=list_discovered_items(
            db,
            status=status,
            protocol=protocol,
            source=source,
            limit=limit,
        )
    )
