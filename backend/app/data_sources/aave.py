from typing import Any

from app.data_sources.base import DataSourceAdapter, unknown_fields


class AaveAdapter(DataSourceAdapter):
    name = "aave"
    required_fields = [
        "reserve_asset",
        "supply_apy",
        "borrow_apy",
        "liquidation_threshold",
    ]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        manual_inputs = query.get("manual_inputs") or {}
        return {
            "reserve_asset": manual_inputs.get("reserve_asset")
            or manual_inputs.get("collateral_asset"),
            "supply_apy": manual_inputs.get("supply_apy"),
            "borrow_apy": manual_inputs.get("borrow_apy"),
            "liquidation_threshold": manual_inputs.get("liquidation_threshold"),
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = {
            "reserve_asset": raw.get("reserve_asset"),
            "supply_apy": raw.get("supply_apy"),
            "borrow_apy": raw.get("borrow_apy"),
            "liquidation_threshold": raw.get("liquidation_threshold"),
        }
        return {
            "source": self.name,
            "status": "manual_fallback",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": [
                "Aave live reserve integration is deferred; normalized values come from manual inputs when present."
            ],
        }
