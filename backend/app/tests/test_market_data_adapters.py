from fastapi.testclient import TestClient

from app.data_sources.base import DataSourceAdapter
from app.data_sources.manual import ManualAdapter
from app.data_sources.morpho import MorphoAdapter
from app.db.session import SessionLocal
from app.main import app
from app.schemas.market_data import MarketDataRequest
from app.services.market_data_service import _run_adapter, fetch_market_data_summary


class FlakyAdapter(DataSourceAdapter):
    name = "flaky_test"

    def __init__(self) -> None:
        self.should_fail = False

    def fetch(self, query: dict) -> dict:
        if self.should_fail:
            raise RuntimeError("simulated failure")
        return {"value": 42}

    def normalize(self, raw: dict) -> dict:
        return {
            "source": self.name,
            "status": "live",
            "data": raw,
            "missing_fields": [],
            "assumptions": [],
        }


def test_manual_adapter_normalizes_user_values() -> None:
    adapter = ManualAdapter()

    normalized = adapter.normalize(
        adapter.fetch(
            {
                "manual_inputs": {
                    "borrow_apy": 0.07,
                    "implied_apy": 0.12,
                    "liquidity_usd": 1_000_000,
                    "ltv": 0.5,
                    "lltv": 0.86,
                    "collateral_asset": "wstETH",
                    "debt_asset": "USDC",
                }
            }
        )
    )

    assert normalized["source"] == "manual"
    assert normalized["status"] == "manual"
    assert normalized["data"]["borrow_apy"] == 0.07
    assert "maturity_date" in normalized["missing_fields"]


def test_protocol_adapter_uses_manual_fallback() -> None:
    adapter = MorphoAdapter()

    normalized = adapter.normalize(
        adapter.fetch(
            {
                "market_url": "https://app.morpho.org/example",
                "manual_inputs": {
                    "collateral_asset": "wstETH",
                    "debt_asset": "USDC",
                    "lltv": 0.86,
                    "borrow_apy": 0.04,
                },
            }
        )
    )

    assert normalized["source"] == "morpho"
    assert normalized["status"] == "manual_fallback"
    assert normalized["missing_fields"] == []


def test_market_data_service_marks_missing_fields() -> None:
    with SessionLocal() as db:
        response = fetch_market_data_summary(
            MarketDataRequest(
                protocols=["pendle", "morpho"],
                manual_inputs={"borrow_apy": 0.05, "liquidity_usd": 250_000},
            ),
            db,
        )

    assert response.status == "partial"
    assert response.source == "aggregated_market_data"
    assert "manual.implied_apy" in response.missing_fields
    assert "pendle.implied_apy" in response.missing_fields
    assert response.data["adapters"]


def test_market_data_endpoint_does_not_crash_on_missing_live_data() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/market-data/fetch",
            json={
                "protocols": ["pendle", "morpho"],
                "manual_inputs": {"borrow_apy": 0.07},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["source"] == "aggregated_market_data"
    assert payload["missing_fields"]


def test_cache_fallback_is_used_when_adapter_fails() -> None:
    adapter = FlakyAdapter()
    query = {"protocols": ["pendle"], "market_url": None, "manual_inputs": {}}

    with SessionLocal() as db:
        live_result = _run_adapter(adapter, query, db, allow_live=True)
        adapter.should_fail = True
        cached_result = _run_adapter(adapter, query, db, allow_live=True)

    assert live_result["status"] == "live"
    assert cached_result["status"] == "cached"
    assert cached_result["data"]["value"] == 42
