from fastapi import APIRouter

from app.simulation.schemas import SimulationRequest, SimulationResponse
from app.simulation.simulator import run_strategy_simulation

router = APIRouter(tags=["simulation"])


@router.post("/simulation/run", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest) -> SimulationResponse:
    return run_strategy_simulation(request)
