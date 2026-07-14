from datetime import UTC, datetime, timedelta
from typing import Any

from app.discovery.schemas import DiscoveryFilters


def passes_protocol_filter(item: dict[str, Any], filters: DiscoveryFilters) -> bool:
    protocol = _clean(item.get("name") or item.get("protocol") or item.get("project"))
    category = _clean(item.get("category"))
    chain = _clean(item.get("chain") or item.get("chains", [None])[0])
    tvl = _number(item.get("tvl") or item.get("tvlUsd") or item.get("totalValueLockedUSD"))

    if filters.protocol_allowlist and protocol not in _clean_set(filters.protocol_allowlist):
        return False
    if filters.protocol_blocklist and protocol in _clean_set(filters.protocol_blocklist):
        return False
    if filters.category_allowlist and category not in _clean_set(filters.category_allowlist):
        return False
    if filters.chain_allowlist and chain and chain not in _clean_set(filters.chain_allowlist):
        return False
    if filters.min_tvl_usd is not None and tvl is not None and tvl < filters.min_tvl_usd:
        return False
    if filters.new_since_days is not None and not _is_recent(item, filters.new_since_days):
        return False
    return True


def passes_pool_filter(item: dict[str, Any], filters: DiscoveryFilters) -> bool:
    project = _clean(item.get("project") or item.get("protocol"))
    chain = _clean(item.get("chain"))
    tvl = _number(item.get("tvlUsd") or item.get("tvl"))

    if filters.protocol_allowlist and project not in _clean_set(filters.protocol_allowlist):
        return False
    if filters.protocol_blocklist and project in _clean_set(filters.protocol_blocklist):
        return False
    if filters.chain_allowlist and chain and chain not in _clean_set(filters.chain_allowlist):
        return False
    if filters.min_pool_tvl_usd is not None and tvl is not None and tvl < filters.min_pool_tvl_usd:
        return False
    return True


def _clean(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip().lower()


def _clean_set(values: list[str]) -> set[str]:
    return {_clean(value) for value in values if value}


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_recent(item: dict[str, Any], days: int) -> bool:
    value = item.get("listedAt") or item.get("createdAt") or item.get("timestamp")
    if not value:
        return True
    try:
        if isinstance(value, (int, float)):
            parsed = datetime.fromtimestamp(float(value), UTC)
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return True
    return parsed >= datetime.now(UTC) - timedelta(days=days)
