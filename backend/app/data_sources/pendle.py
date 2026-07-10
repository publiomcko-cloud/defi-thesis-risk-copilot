from typing import Any

from app.data_sources.base import DataSourceAdapter, unknown_fields


class PendleAdapter(DataSourceAdapter):
    name = "pendle"
    required_fields = ["pt_price", "implied_apy", "maturity_date", "liquidity_usd"]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        manual_inputs = query.get("manual_inputs") or {}
        return {
            "market_url": query.get("market_url"),
            "pt_price": manual_inputs.get("pt_price"),
            "implied_apy": manual_inputs.get("implied_apy"),
            "maturity_date": manual_inputs.get("maturity_date"),
            "liquidity_usd": manual_inputs.get("liquidity_usd"),
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = {
            "market_url": raw.get("market_url"),
            "pt_price": raw.get("pt_price"),
            "implied_apy": raw.get("implied_apy"),
            "maturity_date": raw.get("maturity_date"),
            "liquidity_usd": raw.get("liquidity_usd"),
        }
        return {
            "source": self.name,
            "status": "manual_fallback",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": [
                "Pendle starts as a manual fallback adapter; live market integration is a future step."
            ],
        }
