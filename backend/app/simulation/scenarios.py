from app.simulation.ltv import (
    current_ltv,
    liquidation_buffer,
    shocked_liquidation_buffer,
    shocked_ltv,
)
from app.simulation.schemas import SimulationRequest, SimulationScenario
from app.simulation.spread import base_yield_apy, net_spread_apy


def build_simulation_scenarios(request: SimulationRequest) -> list[SimulationScenario]:
    return [
        _net_spread(request),
        _borrow_apy_shock(request),
        _liquidity_slippage_shock(request),
        _collateral_drawdown(request),
        _early_exit(request),
        _incentive_removal(request),
        _combined_adverse(request),
    ]


def _net_spread(request: SimulationRequest) -> SimulationScenario:
    missing = _missing_yield_and_borrow(request)
    spread = net_spread_apy(request)
    return SimulationScenario(
        name="Net spread estimate",
        scenario_type="net_spread",
        result={"net_spread_apy": spread},
        formula="(implied_apy or supply_apy) + incentive_apy - borrow_apy",
        assumptions=["APY inputs are annualized decimal values."],
        missing_data=missing,
        interpretation=_spread_interpretation(spread, missing),
    )


def _borrow_apy_shock(request: SimulationRequest) -> SimulationScenario:
    missing = _missing_yield_and_borrow(request)
    base_yield = base_yield_apy(request)
    shocked_borrow = (
        request.borrow_apy * request.borrow_apy_shock_multiplier
        if request.borrow_apy is not None
        else None
    )
    shocked_spread = (
        base_yield + (request.incentive_apy or 0) - shocked_borrow
        if base_yield is not None and shocked_borrow is not None
        else None
    )
    return SimulationScenario(
        name="Borrow APY shock",
        scenario_type="borrow_apy_shock",
        result={
            "borrow_apy_shock_multiplier": request.borrow_apy_shock_multiplier,
            "shocked_borrow_apy": shocked_borrow,
            "shocked_net_spread_apy": shocked_spread,
        },
        formula="((implied_apy or supply_apy) + incentive_apy) - (borrow_apy * shock_multiplier)",
        assumptions=["Borrow APY shock is deterministic and does not forecast future rates."],
        missing_data=missing,
        interpretation=_spread_interpretation(shocked_spread, missing),
    )


def _liquidity_slippage_shock(request: SimulationRequest) -> SimulationScenario:
    missing = []
    if request.liquidity_usd is None:
        missing.append("liquidity_usd")
    shocked_liquidity = (
        request.liquidity_usd * (1 - request.liquidity_shock_pct)
        if request.liquidity_usd is not None
        else None
    )
    shocked_slippage_bps = (
        request.slippage_bps / (1 - request.liquidity_shock_pct)
        if request.slippage_bps is not None and request.liquidity_shock_pct < 1
        else None
    )
    return SimulationScenario(
        name="Liquidity and slippage shock",
        scenario_type="liquidity_slippage_shock",
        result={
            "liquidity_shock_pct": request.liquidity_shock_pct,
            "shocked_liquidity_usd": shocked_liquidity,
            "estimated_shocked_slippage_bps": shocked_slippage_bps,
        },
        formula="liquidity_usd * (1 - liquidity_shock_pct); slippage_bps / (1 - liquidity_shock_pct)",
        assumptions=["Slippage estimate is a simple inverse-liquidity approximation when slippage_bps is provided."],
        missing_data=missing,
        interpretation=(
            "Lower liquidity can make exits more uncertain and may increase price impact."
            if not missing
            else "Liquidity impact cannot be estimated without liquidity_usd."
        ),
    )


def _collateral_drawdown(request: SimulationRequest) -> SimulationScenario:
    missing = []
    if current_ltv(request) is None:
        missing.append("ltv or collateral_value_usd/debt_value_usd")
    if request.lltv is None:
        missing.append("lltv")
    new_ltv = shocked_ltv(request)
    buffer = liquidation_buffer(request)
    shocked_buffer = shocked_liquidation_buffer(request)
    return SimulationScenario(
        name="Collateral drawdown and liquidation buffer",
        scenario_type="collateral_drawdown",
        result={
            "collateral_drawdown_pct": request.collateral_drawdown_pct,
            "current_ltv": current_ltv(request),
            "current_liquidation_buffer": buffer,
            "shocked_ltv": new_ltv,
            "shocked_liquidation_buffer": shocked_buffer,
        },
        formula="shocked_ltv = current_ltv / (1 - collateral_drawdown_pct); buffer = lltv - ltv",
        assumptions=["LLTV is treated as the liquidation threshold proxy."],
        missing_data=missing,
        interpretation=(
            "Negative shocked buffer means the deterministic stress crosses the supplied LLTV proxy."
            if shocked_buffer is not None and shocked_buffer < 0
            else "Collateral drawdown reduces the available borrowing buffer."
        ),
    )


def _early_exit(request: SimulationRequest) -> SimulationScenario:
    missing = []
    if request.pt_price is None:
        missing.append("pt_price")
    stressed_price = (
        request.pt_price * (1 - request.early_exit_discount_pct)
        if request.pt_price is not None
        else None
    )
    return SimulationScenario(
        name="Early exit before maturity",
        scenario_type="early_exit",
        result={
            "early_exit_discount_pct": request.early_exit_discount_pct,
            "stressed_exit_price": stressed_price,
            "maturity_date": request.maturity_date,
        },
        formula="stressed_exit_price = pt_price * (1 - early_exit_discount_pct)",
        assumptions=["Early-exit discount is user-provided or defaulted; it is not a price forecast."],
        missing_data=missing,
        interpretation=(
            "Early exit may realize worse pricing than holding to maturity."
            if not missing
            else "Early-exit price impact cannot be estimated without pt_price."
        ),
    )


def _incentive_removal(request: SimulationRequest) -> SimulationScenario:
    missing = _missing_yield_and_borrow(request)
    base_yield = base_yield_apy(request)
    spread_without_incentives = (
        base_yield - request.borrow_apy
        if base_yield is not None and request.borrow_apy is not None
        else None
    )
    return SimulationScenario(
        name="Incentive removal",
        scenario_type="incentive_removal",
        result={
            "removed_incentive_apy": request.incentive_apy or 0,
            "net_spread_without_incentives_apy": spread_without_incentives,
        },
        formula="(implied_apy or supply_apy) - borrow_apy",
        assumptions=["Temporary incentives are set to zero in this scenario."],
        missing_data=missing,
        interpretation=_spread_interpretation(spread_without_incentives, missing),
    )


def _combined_adverse(request: SimulationRequest) -> SimulationScenario:
    missing = _missing_yield_and_borrow(request)
    if request.liquidity_usd is None:
        missing.append("liquidity_usd")
    if shocked_liquidation_buffer(request) is None:
        if current_ltv(request) is None:
            missing.append("ltv or collateral_value_usd/debt_value_usd")
        if request.lltv is None:
            missing.append("lltv")
    missing = sorted(set(missing))
    base_yield = base_yield_apy(request)
    shocked_borrow = (
        request.borrow_apy * request.borrow_apy_shock_multiplier
        if request.borrow_apy is not None
        else None
    )
    combined_spread = (
        base_yield - shocked_borrow
        if base_yield is not None and shocked_borrow is not None
        else None
    )
    return SimulationScenario(
        name="Combined adverse scenario",
        scenario_type="combined_adverse",
        result={
            "shocked_net_spread_without_incentives_apy": combined_spread,
            "shocked_liquidation_buffer": shocked_liquidation_buffer(request),
            "shocked_liquidity_usd": (
                request.liquidity_usd * (1 - request.liquidity_shock_pct)
                if request.liquidity_usd is not None
                else None
            ),
        },
        formula="base_yield - shocked_borrow_apy; lltv - shocked_ltv; liquidity_usd * (1 - liquidity_shock_pct)",
        assumptions=["Combines borrow-rate shock, incentive removal, collateral drawdown, and liquidity shock."],
        missing_data=missing,
        interpretation="Multiple adverse changes can interact and should be reviewed as uncertainty, not a prediction.",
    )


def _missing_yield_and_borrow(request: SimulationRequest) -> list[str]:
    missing = []
    if base_yield_apy(request) is None:
        missing.append("implied_apy or supply_apy")
    if request.borrow_apy is None:
        missing.append("borrow_apy")
    return missing


def _spread_interpretation(spread: float | None, missing: list[str]) -> str:
    if missing:
        return "Net spread cannot be estimated until the missing fields are provided."
    if spread is not None and spread < 0:
        return "The deterministic spread is negative under these assumptions."
    return "The deterministic spread remains non-negative under these assumptions."
