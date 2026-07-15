from fastapi import APIRouter, Depends

from app.core.public_demo import enforce_public_compute_rate_limit
from app.simulation.schemas import SimulationRequest, SimulationResponse
from app.simulation.simulator import run_strategy_simulation

router = APIRouter(tags=["simulation"])


@router.post(
    "/simulation/run",
    response_model=SimulationResponse,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def run_simulation(request: SimulationRequest) -> SimulationResponse:
    return run_strategy_simulation(request)
