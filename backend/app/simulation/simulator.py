from typing import Any

from app.schemas.market_data import MarketDataResponse
from app.simulation.scenarios import build_simulation_scenarios
from app.simulation.schemas import SimulationRequest, SimulationResponse

SIMULATION_DISCLAIMER = (
    "Simulation outputs are deterministic educational scenarios based only on supplied inputs. "
    "They are not forecasts, guarantees, recommendations, or instructions to enter or exit a position."
)


def run_strategy_simulation(request: SimulationRequest) -> SimulationResponse:
    scenarios = build_simulation_scenarios(request)
    missing_data = sorted(
        {field for scenario in scenarios for field in scenario.missing_data}
    )
    assumptions = [
        "All APY values are decimal annual rates.",
        "Scenarios are deterministic stress calculations, not probability-weighted forecasts.",
        "Missing inputs are reported instead of inferred.",
    ]
    return SimulationResponse(
        status="partial" if missing_data else "completed",
        scenarios=scenarios,
        assumptions=assumptions,
        missing_data=missing_data,
        disclaimer=SIMULATION_DISCLAIMER,
    )


def simulation_request_from_market_data(
    market_data: MarketDataResponse,
    strategy_description: str,
    protocols: list[str],
) -> SimulationRequest:
    values: dict[str, Any] = {}
    for adapter in market_data.data.get("adapters", []):
        data = adapter.get("data", {})
        if isinstance(data, dict):
            for key, value in data.items():
                if value is not None and key not in values:
                    values[key] = value

    return SimulationRequest(
        strategy_description=strategy_description,
        protocols=protocols,
        implied_apy=_number(values.get("implied_apy")),
        supply_apy=_number(values.get("supply_apy")),
        borrow_apy=_number(values.get("borrow_apy")),
        ltv=_number(values.get("ltv")),
        lltv=_number(values.get("lltv")),
        liquidity_usd=_number(values.get("liquidity_usd")),
        pt_price=_number(values.get("pt_price")),
        maturity_date=values.get("maturity_date"),
    )


def summarize_simulation(response: SimulationResponse) -> str:
    lines = [
        f"Simulation status: {response.status}.",
        "These deterministic scenarios are educational and are not guarantees.",
    ]
    for scenario in response.scenarios:
        result_items = ", ".join(
            f"{key}: {value}" for key, value in scenario.result.items() if value is not None
        )
        missing = (
            f" Missing data: {', '.join(scenario.missing_data)}."
            if scenario.missing_data
            else ""
        )
        lines.append(
            f"{scenario.name}: {result_items or 'insufficient inputs'}. "
            f"{scenario.interpretation}{missing}"
        )
    return "\n".join(lines)


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
