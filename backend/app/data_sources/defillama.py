from typing import Any

import httpx

from app.data_sources.base import DataSourceAdapter, unknown_fields


class DefiLlamaAdapter(DataSourceAdapter):
    name = "defillama"
    required_fields = ["protocol_tvl_usd", "category"]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        protocol = (query.get("protocol") or "").lower()
        if not protocol:
            raise ValueError("protocol is required")
        response = httpx.get(f"https://api.llama.fi/protocol/{protocol}", timeout=4)
        response.raise_for_status()
        return response.json()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = {
            "protocol_tvl_usd": raw.get("tvl"),
            "category": raw.get("category"),
            "chains": raw.get("chains") or [],
            "slug": raw.get("slug"),
        }
        return {
            "source": self.name,
            "status": "live",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": ["DefiLlama data is public and may be delayed."],
        }
