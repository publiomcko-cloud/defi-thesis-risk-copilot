from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.discovered_item import DiscoveredItemModel
from app.models.source_watch import SourceWatchModel
from app.monitoring.collectors import DEFAULT_COLLECTORS, SourceCollector
from app.monitoring.normalizer import normalize_discovered_item
from app.monitoring.schemas import (
    DiscoveredItem,
    MonitoringFailure,
    MonitoringRunRequest,
    MonitoringRunResponse,
    SourceWatch,
)
from app.monitoring.sources import DEFAULT_SOURCE_WATCHES


def run_monitoring(
    request: MonitoringRunRequest,
    db: Session,
    collectors: dict[str, SourceCollector] | None = None,
) -> MonitoringRunResponse:
    active_collectors = collectors or DEFAULT_COLLECTORS
    _ensure_default_source_watches(db)
    watches = _load_enabled_watches(request, db)
    failures: list[MonitoringFailure] = []
    touched_items: list[DiscoveredItem] = []
    created_count = 0
    duplicate_count = 0
    now = datetime.now(UTC)

    for watch_record in watches:
        watch_record.last_run_at = now
        watch = _watch_schema(watch_record)
        collector = active_collectors.get(watch.source)
        if collector is None:
            watch_record.last_error = f"No collector configured for source '{watch.source}'."
            failures.append(
                MonitoringFailure(
                    source_watch_id=watch.id,
                    source=watch.source,
                    error=watch_record.last_error,
                )
            )
            continue

        try:
            raw_items = collector.collect(watch)
            for raw_item in raw_items:
                item, created = _upsert_discovered_item(raw_item, now, db)
                touched_items.append(_item_schema(item))
                if created:
                    created_count += 1
                else:
                    duplicate_count += 1
            watch_record.last_success_at = now
            watch_record.last_error = None
        except Exception as exc:
            watch_record.last_error = f"{type(exc).__name__}: {exc}"
            failures.append(
                MonitoringFailure(
                    source_watch_id=watch.id,
                    source=watch.source,
                    error=watch_record.last_error,
                )
            )

    db.commit()
    return MonitoringRunResponse(
        status="partial" if failures else "completed",
        watches_checked=len(watches),
        created_count=created_count,
        duplicate_count=duplicate_count,
        failed_count=len(failures),
        failures=failures,
        discovered_items=touched_items,
    )


def list_discovered_items(
    db: Session,
    status: str | None = None,
    protocol: str | None = None,
    source: str | None = None,
    limit: int = 100,
) -> list[DiscoveredItem]:
    _ensure_default_source_watches(db)
    statement = select(DiscoveredItemModel).order_by(DiscoveredItemModel.last_seen_at.desc())
    if status:
        statement = statement.where(DiscoveredItemModel.status == status)
    if protocol:
        statement = statement.where(DiscoveredItemModel.protocol == protocol.lower())
    if source:
        statement = statement.where(DiscoveredItemModel.source == source.lower())
    return [
        _item_schema(item)
        for item in db.execute(statement.limit(limit)).scalars().all()
    ]


def _ensure_default_source_watches(db: Session) -> None:
    existing_ids = set(db.execute(select(SourceWatchModel.id)).scalars().all())
    for watch in DEFAULT_SOURCE_WATCHES:
        if watch.id in existing_ids:
            continue
        db.add(
            SourceWatchModel(
                id=watch.id,
                source=watch.source,
                source_type=watch.source_type,
                protocol=watch.protocol,
                url=watch.url,
                enabled=watch.enabled,
                config_json=watch.config,
            )
        )
    db.commit()


def _load_enabled_watches(
    request: MonitoringRunRequest,
    db: Session,
) -> list[SourceWatchModel]:
    statement = select(SourceWatchModel).where(SourceWatchModel.enabled.is_(True))
    if request.source:
        statement = statement.where(SourceWatchModel.source == request.source.lower())
    if request.protocol:
        statement = statement.where(SourceWatchModel.protocol == request.protocol.lower())
    return list(db.execute(statement).scalars().all())


def _upsert_discovered_item(
    raw_item,
    now: datetime,
    db: Session,
) -> tuple[DiscoveredItemModel, bool]:
    normalized = normalize_discovered_item(raw_item)
    existing = db.execute(
        select(DiscoveredItemModel).where(
            DiscoveredItemModel.discovery_key == normalized["discovery_key"]
        )
    ).scalars().first()
    if existing is not None:
        existing.last_seen_at = now
        existing.raw_payload = normalized["raw_payload"]
        return existing, False

    item = DiscoveredItemModel(
        id=f"disc_{uuid4().hex[:12]}",
        discovered_at=now,
        last_seen_at=now,
        status="needs_review",
        **normalized,
    )
    db.add(item)
    return item, True


def _watch_schema(record: SourceWatchModel) -> SourceWatch:
    return SourceWatch(
        id=record.id,
        source=record.source,
        source_type=record.source_type,
        protocol=record.protocol,
        url=record.url,
        enabled=record.enabled,
        config=record.config_json,
    )


def _item_schema(record: DiscoveredItemModel) -> DiscoveredItem:
    return DiscoveredItem(
        id=record.id,
        source=record.source,
        source_type=record.source_type,
        title=record.title,
        url=record.url,
        protocol=record.protocol,
        chain=record.chain,
        asset=record.asset,
        market_identifier=record.market_identifier,
        discovered_at=record.discovered_at,
        last_seen_at=record.last_seen_at,
        raw_payload=record.raw_payload,
        status=record.status,
    )
