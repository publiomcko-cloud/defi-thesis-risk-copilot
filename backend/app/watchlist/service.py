from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.policies import can_read_resource, can_update_resource
from app.auth.schemas import UserContext
from app.models.alert_event import AlertEventModel
from app.models.watchlist_item import WatchlistItemModel
from app.quotas.service import RESOURCE_WATCHLISTS, enforce_resource_count_limit
from app.watchlist.rules import evaluate_rules
from app.watchlist.schemas import (
    AlertEvent,
    WatchlistCreateResponse,
    WatchlistEvaluationResponse,
    WatchlistItem,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistUpdateResponse,
)

ALERT_STATUSES = {"open", "acknowledged", "archived"}


def create_watchlist_item(
    request: WatchlistItemCreate,
    db: Session,
    actor: UserContext | None = None,
) -> WatchlistCreateResponse:
    if actor is not None:
        enforce_resource_count_limit(db, actor, RESOURCE_WATCHLISTS)
    item = WatchlistItemModel(
        id=f"watch_{uuid4().hex[:12]}",
        item_type=request.item_type,
        title=request.title,
        protocol=request.protocol.lower() if request.protocol else None,
        market_identifier=request.market_identifier,
        source_url=request.source_url,
        rules_json=request.rules,
        snapshot_json=request.snapshot,
        enabled=True,
        owner_user_id=None if actor is None or actor.anonymous_session_id else actor.id,
        anonymous_session_id=actor.anonymous_session_id if actor else None,
        visibility="private" if actor else "public_demo",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistCreateResponse(item=_item_schema(item))


def list_watchlist_items(db: Session, actor: UserContext | None = None) -> list[WatchlistItem]:
    records = db.execute(
        select(WatchlistItemModel).order_by(WatchlistItemModel.created_at.desc())
    ).scalars().all()
    return [_item_schema(record) for record in records if can_read_resource(actor, record, db)]


def update_watchlist_item(
    watchlist_item_id: str,
    request: WatchlistItemUpdate,
    db: Session,
    actor: UserContext | None = None,
) -> WatchlistUpdateResponse:
    item = db.get(WatchlistItemModel, watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    if actor is not None and not can_update_resource(actor, item, db):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    if request.rules is not None:
        item.rules_json = request.rules
    if request.snapshot is not None:
        item.snapshot_json = request.snapshot
    if request.enabled is not None:
        item.enabled = request.enabled
    db.commit()
    db.refresh(item)
    return WatchlistUpdateResponse(item=_item_schema(item))


def evaluate_watchlist_item(
    watchlist_item_id: str,
    db: Session,
    actor: UserContext | None = None,
) -> WatchlistEvaluationResponse:
    item = db.get(WatchlistItemModel, watchlist_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    if actor is not None and not can_update_resource(actor, item, db):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    if not item.enabled:
        raise HTTPException(status_code=409, detail="Watchlist item is disabled")

    candidates, evaluated_rules = evaluate_rules(
        item.title,
        item.rules_json,
        item.snapshot_json,
    )
    created_alerts = []
    now = datetime.now(UTC)
    for candidate in candidates:
        existing_open_alert = _find_open_alert(item.id, candidate.alert_type, db)
        if existing_open_alert is not None:
            continue
        alert = AlertEventModel(
            id=f"alert_{uuid4().hex[:12]}",
            watchlist_item_id=item.id,
            alert_type=candidate.alert_type,
            severity=candidate.severity,
            title=candidate.title,
            message=candidate.message,
            trigger_value=candidate.trigger_value,
            threshold_value=candidate.threshold_value,
            status="open",
            metadata_json=candidate.metadata,
            created_at=now,
            updated_at=now,
        )
        db.add(alert)
        created_alerts.append(alert)

    item.last_evaluated_at = now
    db.commit()
    db.refresh(item)
    for alert in created_alerts:
        db.refresh(alert)

    return WatchlistEvaluationResponse(
        status="completed",
        watchlist_item=_item_schema(item),
        created_alerts=[_alert_schema(alert) for alert in created_alerts],
        evaluated_rules=evaluated_rules,
    )


def _find_open_alert(
    watchlist_item_id: str,
    alert_type: str,
    db: Session,
) -> AlertEventModel | None:
    return db.execute(
        select(AlertEventModel)
        .where(AlertEventModel.watchlist_item_id == watchlist_item_id)
        .where(AlertEventModel.alert_type == alert_type)
        .where(AlertEventModel.status == "open")
        .order_by(AlertEventModel.created_at.desc())
    ).scalars().first()


def list_alert_events(
    db: Session,
    status: str | None = None,
    actor: UserContext | None = None,
) -> list[AlertEvent]:
    statement = select(AlertEventModel).order_by(AlertEventModel.created_at.desc())
    if status:
        statement = statement.where(AlertEventModel.status == status)
    records = db.execute(statement).scalars().all()
    visible = []
    for record in records:
        item = db.get(WatchlistItemModel, record.watchlist_item_id)
        if item is not None and can_read_resource(actor, item, db):
            visible.append(record)
    return [_alert_schema(record) for record in visible]


def update_alert_status(
    alert_id: str,
    status: str,
    db: Session,
    actor: UserContext | None = None,
) -> AlertEvent:
    if status not in ALERT_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported alert status")
    alert = db.get(AlertEventModel, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert event not found")
    item = db.get(WatchlistItemModel, alert.watchlist_item_id)
    if item is None or (actor is not None and not can_update_resource(actor, item, db)):
        raise HTTPException(status_code=404, detail="Alert event not found")
    alert.status = status
    alert.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return _alert_schema(alert)


def _item_schema(record: WatchlistItemModel) -> WatchlistItem:
    return WatchlistItem(
        id=record.id,
        item_type=record.item_type,
        title=record.title,
        protocol=record.protocol,
        market_identifier=record.market_identifier,
        source_url=record.source_url,
        rules=record.rules_json,
        snapshot=record.snapshot_json,
        enabled=record.enabled,
        created_at=record.created_at,
        last_evaluated_at=record.last_evaluated_at,
    )


def _alert_schema(record: AlertEventModel) -> AlertEvent:
    return AlertEvent(
        id=record.id,
        watchlist_item_id=record.watchlist_item_id,
        alert_type=record.alert_type,
        severity=record.severity,
        title=record.title,
        message=record.message,
        trigger_value=record.trigger_value,
        threshold_value=record.threshold_value,
        status=record.status,
        metadata=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
