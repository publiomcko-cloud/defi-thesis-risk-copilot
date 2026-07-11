from typing import Protocol

from app.monitoring.schemas import RawDiscoveredItem, SourceWatch


class SourceCollector(Protocol):
    source: str

    def collect(self, watch: SourceWatch) -> list[RawDiscoveredItem]:
        raise NotImplementedError


class StaticSourceCollector:
    """Deterministic collector used until live source-specific APIs are expanded."""

    def __init__(self, source: str, items: list[dict]) -> None:
        self.source = source
        self._items = items

    def collect(self, watch: SourceWatch) -> list[RawDiscoveredItem]:
        return [
            RawDiscoveredItem(
                source=watch.source,
                source_type=item.get("source_type") or watch.source_type,
                title=item["title"],
                url=item.get("url") or watch.url,
                protocol=item.get("protocol") or watch.protocol,
                chain=item.get("chain"),
                asset=item.get("asset"),
                market_identifier=item.get("market_identifier"),
                raw_payload={"watch_id": watch.id, **item},
            )
            for item in self._items
        ]


DEFAULT_COLLECTORS: dict[str, SourceCollector] = {
    "pendle": StaticSourceCollector(
        "pendle",
        [
            {
                "title": "Pendle PT market discovery candidate",
                "url": "https://app.pendle.finance/trade/markets",
                "protocol": "pendle",
                "chain": "ethereum",
                "asset": "PT",
                "market_identifier": "pendle:markets:index",
            }
        ],
    ),
    "morpho": StaticSourceCollector(
        "morpho",
        [
            {
                "title": "Morpho market discovery candidate",
                "url": "https://app.morpho.org/markets",
                "protocol": "morpho",
                "chain": "ethereum",
                "asset": "USDC",
                "market_identifier": "morpho:markets:index",
            }
        ],
    ),
    "aave": StaticSourceCollector(
        "aave",
        [
            {
                "title": "Aave reserve discovery candidate",
                "url": "https://app.aave.com/reserve-overview",
                "protocol": "aave",
                "chain": "ethereum",
                "asset": "USDC",
                "market_identifier": "aave:reserve:usdc",
            }
        ],
    ),
    "defillama": StaticSourceCollector(
        "defillama",
        [
            {
                "title": "DefiLlama yield pool discovery candidate",
                "url": "https://yields.llama.fi/pools",
                "source_type": "yield_data",
                "chain": "ethereum",
                "market_identifier": "defillama:yields:pools",
            }
        ],
    ),
    "protocol_docs": StaticSourceCollector(
        "protocol_docs",
        [
            {
                "title": "Pendle protocol documentation candidate",
                "url": "https://docs.pendle.finance/",
                "protocol": "pendle",
                "source_type": "documentation",
                "market_identifier": "docs:pendle:index",
            }
        ],
    ),
    "governance_forums": StaticSourceCollector(
        "governance_forums",
        [
            {
                "title": "Morpho governance forum candidate",
                "url": "https://gov.morpho.org/",
                "protocol": "morpho",
                "source_type": "governance",
                "market_identifier": "governance:morpho:index",
            }
        ],
    ),
    "risk_audits": StaticSourceCollector(
        "risk_audits",
        [
            {
                "title": "Aave security and audit links candidate",
                "url": "https://docs.aave.com/developers/deployed-contracts/security-and-audits",
                "protocol": "aave",
                "source_type": "risk_report",
                "market_identifier": "audit:aave:index",
            }
        ],
    ),
}
