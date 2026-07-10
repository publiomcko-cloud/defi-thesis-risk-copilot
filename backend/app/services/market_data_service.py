from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_sources.aave import AaveAdapter
from app.data_sources.base import DataSourceAdapter
from app.data_sources.coingecko import CoinGeckoAdapter
from app.data_sources.defillama import DefiLlamaAdapter
from app.data_sources.manual import ManualAdapter
from app.data_sources.morpho import MorphoAdapter
from app.data_sources.pendle import PendleAdapter
from app.models.market_data_cache import MarketDataCacheModel
from app.schemas.market_data import MarketDataRequest, MarketDataResponse


PROTOCOL_ADAPTERS: dict[str, type[DataSourceAdapter]] = {
    "pendle": PendleAdapter,
    "morpho": MorphoAdapter,
    "aave": AaveAdapter,
}


def fetch_market_data_summary(
    request: MarketDataRequest,
    db: Session,
) -> MarketDataResponse:
    query = {
        "protocols": [protocol.lower() for protocol in request.protocols],
        "market_url": request.market_url,
        "manual_inputs": request.manual_inputs,
    }
    adapter_results = []

    manual_result = _run_adapter(ManualAdapter(), query, db)
    adapter_results.append(manual_result)

    for protocol in query["protocols"]:
        adapter_cls = PROTOCOL_ADAPTERS.get(protocol)
        if adapter_cls is None:
            continue
        adapter_results.append(_run_adapter(adapter_cls(), {**query, "protocol": protocol}, db))

    if query["protocols"]:
        adapter_results.append(
            _run_adapter(
                DefiLlamaAdapter(),
                {**query, "protocol": query["protocols"][0]},
                db,
                allow_live=True,
            )
        )

    if request.manual_inputs.get("token_id") or request.manual_inputs.get("debt_asset"):
        adapter_results.append(
            _run_adapter(
                CoinGeckoAdapter(),
                {**query, **request.manual_inputs},
                db,
                allow_live=True,
            )
        )

    missing_fields = sorted(
        {
            f"{result['source']}.{field}"
            for result in adapter_results
            for field in result.get("missing_fields", [])
        }
    )
    assumptions = [
        assumption
        for result in adapter_results
        for assumption in result.get("assumptions", [])
    ]
    data = {
        "protocols": query["protocols"],
        "market_url": request.market_url,
        "adapters": adapter_results,
    }
    status = "completed" if not missing_fields else "partial"

    return MarketDataResponse(
        status=status,
        source="aggregated_market_data",
        data=data,
        missing_fields=missing_fields,
        assumptions=assumptions,
    )


def _run_adapter(
    adapter: DataSourceAdapter,
    query: dict,
    db: Session,
    allow_live: bool = False,
) -> dict:
    cache_key = _cache_key(adapter.name, query)
    try:
        raw = adapter.fetch(query) if allow_live or adapter.name != "defillama" else {}
        normalized = adapter.normalize(raw)
        _save_cache(adapter.name, cache_key, normalized, db)
        return normalized
    except Exception as exc:
        cached = _load_cache(adapter.name, cache_key, db)
        if cached is not None:
            cached["status"] = "cached"
            cached.setdefault("assumptions", []).append(
                f"{adapter.name} live fetch failed; using cached data."
            )
            return cached
        return {
            "source": adapter.name,
            "status": "unavailable",
            "data": {},
            "missing_fields": ["live_data"],
            "assumptions": [
                f"{adapter.name} adapter unavailable: {type(exc).__name__}.",
                "No cached data was available; downstream reports must mark this uncertainty.",
            ],
        }


def _cache_key(source: str, query: dict) -> str:
    protocols = ",".join(query.get("protocols") or [])
    market_url = query.get("market_url") or ""
    token_id = (query.get("manual_inputs") or {}).get("token_id") or query.get("token_id") or ""
    return f"{source}:{protocols}:{market_url}:{token_id}"


def _save_cache(source: str, cache_key: str, payload: dict, db: Session) -> None:
    record = MarketDataCacheModel(
        id=f"cache_{uuid4().hex[:12]}",
        source=source,
        cache_key=cache_key,
        payload_json=payload,
        fetched_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    db.add(record)
    db.commit()


def _load_cache(source: str, cache_key: str, db: Session) -> dict | None:
    statement = (
        select(MarketDataCacheModel)
        .where(MarketDataCacheModel.source == source)
        .where(MarketDataCacheModel.cache_key == cache_key)
        .order_by(MarketDataCacheModel.fetched_at.desc())
    )
    record = db.execute(statement).scalars().first()
    if record is None:
        return None
    return dict(record.payload_json)
