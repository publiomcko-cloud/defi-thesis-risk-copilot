from app.discovery.defillama_client import DefiLlamaClient
from app.discovery.filters import passes_pool_filter, passes_protocol_filter
from app.discovery.normalizer import (
    normalize_defillama_overview_item,
    normalize_defillama_pool,
    normalize_defillama_protocol,
    normalize_manual_item,
)
from app.discovery.schemas import DiscoveryFilters, ManualDiscoveryItem
from app.monitoring.schemas import RawDiscoveredItem


class DefiLlamaDiscoveryCollector:
    def __init__(self, client: DefiLlamaClient | None = None) -> None:
        self.client = client or DefiLlamaClient()

    def collect(self, filters: DiscoveryFilters) -> list[RawDiscoveredItem]:
        items: list[RawDiscoveredItem] = []
        for protocol in self.client.protocols():
            if passes_protocol_filter(protocol, filters):
                items.append(normalize_defillama_protocol(protocol))

        if filters.include_yield_pools:
            for pool in self.client.yield_pools():
                if passes_pool_filter(pool, filters):
                    items.append(normalize_defillama_pool(pool))

        if filters.include_options_protocols:
            items.extend(
                normalize_defillama_overview_item(item, "options_protocol")
                for item in self.client.options_overview()
                if passes_protocol_filter(item, filters)
            )

        if filters.include_open_interest:
            items.extend(
                normalize_defillama_overview_item(item, "open_interest_protocol")
                for item in self.client.open_interest_overview()
                if passes_protocol_filter(item, filters)
            )

        if filters.include_fee_protocols:
            items.extend(
                normalize_defillama_overview_item(item, "fee_protocol")
                for item in self.client.fees_overview()
                if passes_protocol_filter(item, filters)
            )

        return items


class ManualDiscoveryCollector:
    def collect(self, items: list[ManualDiscoveryItem]) -> list[RawDiscoveredItem]:
        return [normalize_manual_item(item) for item in items]
