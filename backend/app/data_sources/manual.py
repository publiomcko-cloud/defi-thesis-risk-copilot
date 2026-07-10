from typing import Any

from app.data_sources.base import DataSourceAdapter, unknown_fields


class ManualAdapter(DataSourceAdapter):
    name = "manual"

    required_fields = [
        "borrow_apy",
        "implied_apy",
        "liquidity_usd",
        "maturity_date",
        "ltv",
        "lltv",
        "collateral_asset",
        "debt_asset",
    ]

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        return dict(query.get("manual_inputs") or {})

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        data = {
            "borrow_apy": raw.get("borrow_apy"),
            "implied_apy": raw.get("implied_apy"),
            "liquidity_usd": raw.get("liquidity_usd"),
            "maturity_date": raw.get("maturity_date"),
            "ltv": raw.get("ltv"),
            "lltv": raw.get("lltv"),
            "collateral_asset": raw.get("collateral_asset"),
            "debt_asset": raw.get("debt_asset"),
        }
        return {
            "source": self.name,
            "status": "manual",
            "data": data,
            "missing_fields": unknown_fields(self.required_fields, data),
            "assumptions": ["Manual values are user-provided and unverified."],
        }
