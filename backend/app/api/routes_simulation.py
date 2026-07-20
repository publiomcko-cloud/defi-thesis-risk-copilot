from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.quotas.service import ACTION_SIMULATION, consume_quota
from app.simulation.schemas import SimulationRequest, SimulationResponse
from app.simulation.simulator import run_strategy_simulation

router = APIRouter(tags=["simulation"])


@router.post(
    "/simulation/run",
    response_model=SimulationResponse,
    dependencies=[Depends(enforce_public_compute_rate_limit)],
)
def run_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> SimulationResponse:
    consume_quota(db, actor, ACTION_SIMULATION)
    return run_strategy_simulation(request)
