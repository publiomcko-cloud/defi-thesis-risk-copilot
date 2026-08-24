import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.core.public_demo import enforce_public_compute_rate_limit
from app.db.session import get_db
from app.quotas.service import ACTION_SIMULATION, consume_quota
from app.entitlements.service import emit_usage
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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SimulationResponse:
    consume_quota(db, actor, ACTION_SIMULATION)
    response = run_strategy_simulation(request)
    if actor.auth_enabled and actor.anonymous_session_id is None:
        source_id = hashlib.sha256((idempotency_key or f"request:{uuid4().hex}").encode()).hexdigest()[:48]
        emit_usage(db, owner_user_id=actor.id, unit_key="usage.simulation.completed.v1", source_type="simulation", source_id=source_id)
        db.commit()
    return response
