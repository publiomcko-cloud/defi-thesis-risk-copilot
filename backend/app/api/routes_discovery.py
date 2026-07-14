from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.db.session import get_db
from app.discovery.schemas import DiscoveryRunRequest, DiscoveryRunResponse
from app.discovery.service import list_discovery_candidates, run_discovery
from app.monitoring.schemas import DiscoveredItemsResponse

router = APIRouter(tags=["discovery"])


@router.post("/discovery/run", response_model=DiscoveryRunResponse)
def run_public_discovery(
    request: DiscoveryRunRequest | None = None,
    db: Session = Depends(get_db),
    current_user: UserContext = Depends(require_admin),
) -> DiscoveryRunResponse:
    response = run_discovery(request or DiscoveryRunRequest(), db)
    record_audit_event(
        db,
        current_user.id,
        "discovery.run",
        "discovery",
        None,
        {"created_count": response.created_count, "failed_count": response.failed_count},
    )
    return response


@router.get("/discovery/candidates", response_model=DiscoveredItemsResponse)
def get_discovery_candidates(
    status: str | None = None,
    protocol: str | None = None,
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> DiscoveredItemsResponse:
    return DiscoveredItemsResponse(
        items=list_discovery_candidates(
            db,
            status=status,
            protocol=protocol,
            source=source,
            limit=limit,
        )
    )
