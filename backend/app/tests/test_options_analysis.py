from fastapi.testclient import TestClient

from app.main import app
from app.options.analysis import analyze_option
from app.options.schemas import OptionsAnalysisRequest


def test_call_option_breakeven_and_payoff_scenarios() -> None:
    result = analyze_option(
        OptionsAnalysisRequest(
            option_type="call",
            underlying_asset="ETH",
            underlying_price=3000,
            strike_price=3200,
            premium=150,
            implied_volatility=0.75,
            bid=145,
            ask=155,
            scenario_prices=[2800, 3200, 3500],
        )
    )

    assert result.breakeven_price == 3350
    assert result.max_loss == 150
    assert result.bid_ask_spread == 10
    assert result.scenarios[0].payoff == -150
    assert result.scenarios[1].payoff == -150
    assert result.scenarios[2].payoff == 150
    assert result.scenarios[2].return_on_premium_pct == 100
    assert "not a recommendation to buy or sell" in result.disclaimer


def test_put_option_breakeven_and_max_profit_framing() -> None:
    result = analyze_option(
        OptionsAnalysisRequest(
            option_type="put",
            underlying_price=3000,
            strike_price=2800,
            premium=100,
            scenario_prices=[2500, 2800, 3100],
        )
    )

    assert result.breakeven_price == 2700
    assert result.max_loss == 100
    assert result.scenarios[0].payoff == 200
    assert result.scenarios[0].return_on_premium_pct == 200
    assert result.scenarios[1].payoff == -100
    assert "2700" in result.max_profit
    assert "implied_volatility" in result.missing_data
    assert "bid/ask" in result.missing_data


def test_options_endpoint_returns_non_advisory_output() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/options/analyze",
            json={
                "option_type": "call",
                "underlying_asset": "BTC",
                "underlying_price": 60000,
                "strike_price": 65000,
                "premium": 2000,
                "implied_volatility": 0.65,
                "bid": 1900,
                "ask": 2100,
                "scenario_prices": [55000, 65000, 70000],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["breakeven_price"] == 67000
    assert len(payload["scenarios"]) == 3
    assert "buy or sell" in payload["disclaimer"]


def test_invalid_expiration_date_returns_missing_data_and_risk_note() -> None:
    result = analyze_option(
        OptionsAnalysisRequest(
            option_type="call",
            underlying_price=3000,
            strike_price=3200,
            premium=150,
            expiration_date="not-a-date",
            scenario_prices=[3000],
        )
    )

    assert result.days_to_expiration is None
    assert "valid_expiration_date" in result.missing_data
    assert any("Expiration timing could not be evaluated" in risk for risk in result.risks)


def test_options_endpoint_handles_invalid_expiration_date_without_server_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/options/analyze",
            json={
                "option_type": "put",
                "underlying_price": 3000,
                "strike_price": 2800,
                "premium": 100,
                "expiration_date": "2026-99-99",
                "scenario_prices": [2500],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["days_to_expiration"] is None
    assert "valid_expiration_date" in payload["missing_data"]


def test_options_accepts_percentage_style_implied_volatility() -> None:
    result = analyze_option(
        OptionsAnalysisRequest(
            option_type="call",
            underlying_price=3000,
            strike_price=3200,
            premium=150,
            implied_volatility=75,
            scenario_prices=[3500],
        )
    )

    assert "75.00%" in result.volatility_summary
