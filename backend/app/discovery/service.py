from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.discovery.collectors import DefiLlamaDiscoveryCollector, ManualDiscoveryCollector
from app.discovery.schemas import DiscoveryFailure, DiscoveryRunRequest, DiscoveryRunResponse
from app.evaluation.evaluator import evaluate_discovered_item
from app.models.discovered_item import DiscoveredItemModel
from app.monitoring.discovery_service import _item_schema
from app.monitoring.normalizer import normalize_discovered_item
from app.monitoring.schemas import RawDiscoveredItem


def run_discovery(
    request: DiscoveryRunRequest,
    db: Session,
    defillama_collector: DefiLlamaDiscoveryCollector | None = None,
    manual_collector: ManualDiscoveryCollector | None = None,
) -> DiscoveryRunResponse:
    failures: list[DiscoveryFailure] = []
    raw_items: list[RawDiscoveredItem] = []
    now = datetime.now(UTC)

    if request.include_defillama:
        try:
            raw_items.extend((defillama_collector or DefiLlamaDiscoveryCollector()).collect(request.filters))
        except Exception as exc:
            failures.append(DiscoveryFailure(source="defillama", error=f"{type(exc).__name__}: {exc}"))

    try:
        raw_items.extend((manual_collector or ManualDiscoveryCollector()).collect(request.manual_items))
    except Exception as exc:
        failures.append(DiscoveryFailure(source="manual", error=f"{type(exc).__name__}: {exc}"))

    touched: list[DiscoveredItemModel] = []
    created_count = 0
    duplicate_count = 0
    for raw_item in raw_items:
        item, created = _upsert_raw_discovered_item(raw_item, now, db)
        touched.append(item)
        if created:
            created_count += 1
        else:
            duplicate_count += 1

    evaluated_count = 0
    if request.auto_evaluate and request.evaluation_limit:
        for item in touched[: request.evaluation_limit]:
            evaluate_discovered_item(item.id, db)
            evaluated_count += 1

    db.commit()
    return DiscoveryRunResponse(
        status="partial" if failures else "completed",
        created_count=created_count,
        duplicate_count=duplicate_count,
        evaluated_count=evaluated_count,
        failed_count=len(failures),
        failures=failures,
        candidates=[_item_schema(item) for item in touched],
    )


def list_discovery_candidates(
    db: Session,
    status: str | None = None,
    protocol: str | None = None,
    source: str | None = None,
    limit: int = 100,
):
    statement = select(DiscoveredItemModel).order_by(DiscoveredItemModel.last_seen_at.desc())
    if status:
        statement = statement.where(DiscoveredItemModel.status == status)
    if protocol:
        statement = statement.where(DiscoveredItemModel.protocol == protocol.lower())
    if source:
        statement = statement.where(DiscoveredItemModel.source == source.lower())
    return [_item_schema(item) for item in db.execute(statement.limit(limit)).scalars().all()]


def _upsert_raw_discovered_item(
    raw_item: RawDiscoveredItem,
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
    db.flush()
    return item, True
