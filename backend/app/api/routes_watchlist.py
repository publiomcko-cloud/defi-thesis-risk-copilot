from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import block_public_demo_mutation
from app.db.session import get_db
from app.watchlist.schemas import (
    AlertEventsResponse,
    AlertStatusUpdateRequest,
    AlertStatusUpdateResponse,
    WatchlistCreateResponse,
    WatchlistEvaluationResponse,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistItemsResponse,
    WatchlistUpdateResponse,
)
from app.watchlist.service import (
    create_watchlist_item,
    evaluate_watchlist_item,
    list_alert_events,
    list_watchlist_items,
    update_alert_status,
    update_watchlist_item,
)

router = APIRouter(tags=["watchlist"])


@router.post(
    "/watchlist/items",
    response_model=WatchlistCreateResponse,
    dependencies=[Depends(block_public_demo_mutation)],
)
def create_item(
    request: WatchlistItemCreate,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> WatchlistCreateResponse:
    return create_watchlist_item(request, db, actor)


@router.get("/watchlist/items", response_model=WatchlistItemsResponse)
def get_items(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> WatchlistItemsResponse:
    return WatchlistItemsResponse(items=list_watchlist_items(db, actor))


@router.get("/watchlist", response_model=WatchlistItemsResponse)
def get_watchlist(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> WatchlistItemsResponse:
    return WatchlistItemsResponse(items=list_watchlist_items(db, actor))


@router.patch(
    "/watchlist/items/{watchlist_item_id}",
    response_model=WatchlistUpdateResponse,
    dependencies=[Depends(block_public_demo_mutation)],
)
def patch_item(
    watchlist_item_id: str,
    request: WatchlistItemUpdate,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> WatchlistUpdateResponse:
    return update_watchlist_item(watchlist_item_id, request, db, actor)


@router.post(
    "/watchlist/items/{watchlist_item_id}/evaluate",
    response_model=WatchlistEvaluationResponse,
    dependencies=[Depends(block_public_demo_mutation)],
)
def evaluate_item(
    watchlist_item_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> WatchlistEvaluationResponse:
    return evaluate_watchlist_item(watchlist_item_id, db, actor)


@router.get("/watchlist/alerts", response_model=AlertEventsResponse)
def get_alerts(
    status: str | None = None,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> AlertEventsResponse:
    return AlertEventsResponse(items=list_alert_events(db, status=status, actor=actor))


@router.patch(
    "/watchlist/alerts/{alert_id}",
    response_model=AlertStatusUpdateResponse,
    dependencies=[Depends(block_public_demo_mutation)],
)
def patch_alert(
    alert_id: str,
    request: AlertStatusUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> AlertStatusUpdateResponse:
    return AlertStatusUpdateResponse(alert=update_alert_status(alert_id, request.status, db, actor))
