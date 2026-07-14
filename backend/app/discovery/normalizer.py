from hashlib import sha256
from typing import Any

from app.discovery.quality import source_quality_notes
from app.discovery.schemas import ManualDiscoveryItem
from app.monitoring.schemas import RawDiscoveredItem


def normalize_defillama_protocol(item: dict[str, Any]) -> RawDiscoveredItem:
    name = str(item.get("name") or item.get("protocol") or "Unknown Protocol")
    slug = str(item.get("slug") or name.lower().replace(" ", "-"))
    chains = item.get("chains") if isinstance(item.get("chains"), list) else []
    url = item.get("url") or item.get("twitter") or f"https://defillama.com/protocol/{slug}"
    return RawDiscoveredItem(
        source="defillama",
        source_type="protocol",
        title=f"{name} protocol discovery candidate",
        url=str(url) if url else None,
        protocol=name,
        chain=str(chains[0]) if chains else None,
        market_identifier=f"defillama:protocol:{slug}",
        raw_payload=_with_quality(item, "defillama_protocols"),
    )


def normalize_defillama_pool(item: dict[str, Any]) -> RawDiscoveredItem:
    project = str(item.get("project") or item.get("protocol") or "unknown")
    symbol = str(item.get("symbol") or item.get("pool") or "yield pool")
    chain = item.get("chain")
    pool_id = item.get("pool") or _stable_hash(f"{project}:{symbol}:{chain}")
    return RawDiscoveredItem(
        source="defillama",
        source_type="yield_pool",
        title=f"{project} yield pool: {symbol}",
        url="https://yields.llama.fi/pools",
        protocol=project,
        chain=str(chain) if chain else None,
        asset=symbol,
        market_identifier=f"defillama:yield_pool:{pool_id}",
        raw_payload=_with_quality(item, "defillama_yield_pools"),
    )


def normalize_defillama_overview_item(item: dict[str, Any], source_type: str) -> RawDiscoveredItem:
    name = str(item.get("name") or item.get("protocol") or item.get("displayName") or "unknown")
    category = str(item.get("category") or source_type)
    slug = str(item.get("slug") or name.lower().replace(" ", "-"))
    return RawDiscoveredItem(
        source="defillama",
        source_type=source_type,
        title=f"{name} {category} discovery candidate",
        url=f"https://defillama.com/protocol/{slug}",
        protocol=name,
        chain=str(item.get("chain")) if item.get("chain") else None,
        market_identifier=f"defillama:{source_type}:{slug}",
        raw_payload=_with_quality(item, f"defillama_{source_type}"),
    )


def normalize_manual_item(item: ManualDiscoveryItem) -> RawDiscoveredItem:
    return RawDiscoveredItem(
        source="manual",
        source_type=item.source_type,
        title=item.title,
        url=item.url,
        protocol=item.protocol,
        chain=item.chain,
        asset=item.asset,
        market_identifier=item.market_identifier or f"manual:{_stable_hash(item.title + str(item.url))}",
        raw_payload=_with_quality(item.model_dump(mode="json"), "manual"),
    )


def _with_quality(item: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        **item,
        "source_quality_notes": source_quality_notes(item, source),
    }


def _stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]
