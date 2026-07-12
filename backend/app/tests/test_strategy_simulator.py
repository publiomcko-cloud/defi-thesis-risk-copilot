from fastapi.testclient import TestClient

from app.main import app
from app.simulation.schemas import SimulationRequest
from app.simulation.simulator import run_strategy_simulation


def test_strategy_simulator_returns_deterministic_scenarios() -> None:
    response = run_strategy_simulation(
        SimulationRequest(
            implied_apy=0.12,
            borrow_apy=0.05,
            incentive_apy=0.01,
            ltv=0.5,
            lltv=0.86,
            liquidity_usd=1_000_000,
            pt_price=0.95,
            slippage_bps=30,
        )
    )

    assert response.status == "completed"
    assert len(response.scenarios) == 7
    net_spread = next(
        scenario for scenario in response.scenarios if scenario.scenario_type == "net_spread"
    )
    assert net_spread.result["net_spread_apy"] == 0.08
    assert "not probability-weighted forecasts" in response.assumptions[1]
    assert "not forecasts" in response.disclaimer


def test_strategy_simulator_marks_missing_data_without_inference() -> None:
    response = run_strategy_simulation(SimulationRequest(liquidity_usd=250_000))

    assert response.status == "partial"
    assert "borrow_apy" in response.missing_data
    assert "implied_apy or supply_apy" in response.missing_data
    net_spread = next(
        scenario for scenario in response.scenarios if scenario.scenario_type == "net_spread"
    )
    assert net_spread.result["net_spread_apy"] is None
    assert "cannot be estimated" in net_spread.interpretation


def test_combined_adverse_marks_missing_ltv_and_lltv_data() -> None:
    response = run_strategy_simulation(
        SimulationRequest(
            implied_apy=0.12,
            borrow_apy=0.05,
            liquidity_usd=1_000_000,
        )
    )

    combined = next(
        scenario
        for scenario in response.scenarios
        if scenario.scenario_type == "combined_adverse"
    )

    assert combined.result["shocked_liquidation_buffer"] is None
    assert "ltv or collateral_value_usd/debt_value_usd" in combined.missing_data
    assert "lltv" in combined.missing_data


def test_simulation_endpoint_returns_non_advisory_results() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/simulation/run",
            json={
                "strategy_description": "Pendle PT using Morpho borrow",
                "protocols": ["pendle", "morpho"],
                "implied_apy": 0.1,
                "borrow_apy": 0.06,
                "ltv": 0.55,
                "lltv": 0.86,
                "liquidity_usd": 500000,
                "pt_price": 0.94,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert len(payload["scenarios"]) == 7
    assert "recommendations" in payload["disclaimer"]
    assert "enter or exit" in payload["disclaimer"]
