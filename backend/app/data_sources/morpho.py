from typing import Any

from app.data_sources.base import DataSourceAdapter, unknown_fields


class MorphoAdapter(DataSourceAdapter):
    name = "morpho"
    required_fields = ["collateral_asset", "loan_asset", "lltv", "borrow_apy"]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        manual_inputs = query.get("manual_inputs") or {}
        return {
            "market_url": query.get("market_url"),
            "collateral_asset": manual_inputs.get("collateral_asset"),
            "loan_asset": manual_inputs.get("debt_asset") or manual_inputs.get("loan_asset"),
            "lltv": manual_inputs.get("lltv"),
            "borrow_apy": manual_inputs.get("borrow_apy"),
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = {
            "market_url": raw.get("market_url"),
            "collateral_asset": raw.get("collateral_asset"),
            "loan_asset": raw.get("loan_asset"),
            "lltv": raw.get("lltv"),
            "borrow_apy": raw.get("borrow_apy"),
        }
        return {
            "source": self.name,
            "status": "manual_fallback",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": [
                "Morpho live API integration is deferred; normalized values come from manual inputs when present."
            ],
        }
