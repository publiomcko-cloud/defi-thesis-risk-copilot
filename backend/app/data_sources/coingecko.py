from typing import Any

import httpx

from app.data_sources.base import DataSourceAdapter, unknown_fields


class CoinGeckoAdapter(DataSourceAdapter):
    name = "coingecko"
    required_fields = ["token_price_usd", "market_cap_usd", "volume_24h_usd"]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        token_id = query.get("token_id") or query.get("debt_asset") or "ethereum"
        response = httpx.get(
            f"https://api.coingecko.com/api/v3/coins/{token_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
            timeout=4,
        )
        response.raise_for_status()
        return response.json()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        market_data = raw.get("market_data") or {}
        data = {
            "token_id": raw.get("id"),
            "symbol": raw.get("symbol"),
            "token_price_usd": (market_data.get("current_price") or {}).get("usd"),
            "market_cap_usd": (market_data.get("market_cap") or {}).get("usd"),
            "volume_24h_usd": (market_data.get("total_volume") or {}).get("usd"),
        }
        return {
            "source": self.name,
            "status": "live",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": ["CoinGecko data is public and may be rate limited or delayed."],
        }
