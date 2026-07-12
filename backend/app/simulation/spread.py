from app.simulation.schemas import SimulationRequest


def base_yield_apy(request: SimulationRequest) -> float | None:
    if request.implied_apy is not None:
        return request.implied_apy
    if request.supply_apy is not None:
        return request.supply_apy
    return None


def net_spread_apy(request: SimulationRequest) -> float | None:
    base_yield = base_yield_apy(request)
    if base_yield is None or request.borrow_apy is None:
        return None
    return base_yield + (request.incentive_apy or 0) - request.borrow_apy
