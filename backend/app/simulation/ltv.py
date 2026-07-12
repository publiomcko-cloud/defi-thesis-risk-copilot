from app.simulation.schemas import SimulationRequest


def current_ltv(request: SimulationRequest) -> float | None:
    if request.ltv is not None:
        return request.ltv
    if request.collateral_value_usd and request.debt_value_usd is not None:
        if request.collateral_value_usd == 0:
            return None
        return request.debt_value_usd / request.collateral_value_usd
    return None


def shocked_ltv(request: SimulationRequest) -> float | None:
    ltv = current_ltv(request)
    remaining_collateral_ratio = 1 - request.collateral_drawdown_pct
    if ltv is None or remaining_collateral_ratio <= 0:
        return None
    return ltv / remaining_collateral_ratio


def liquidation_buffer(request: SimulationRequest) -> float | None:
    if request.lltv is None:
        return None
    ltv = current_ltv(request)
    if ltv is None:
        return None
    return request.lltv - ltv


def shocked_liquidation_buffer(request: SimulationRequest) -> float | None:
    if request.lltv is None:
        return None
    ltv = shocked_ltv(request)
    if ltv is None:
        return None
    return request.lltv - ltv
