from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.core.public_demo import block_public_demo_mutation
from app.db.session import get_db
from app.demo.scenarios import DEMO_SCENARIOS, DemoScenario
from app.demo.seed_data import DemoSeedResult, DemoStatus, get_demo_status, seed_demo_data

router = APIRouter(tags=["demo"])


@router.get("/demo/status", response_model=DemoStatus)
def read_demo_status(db: Session = Depends(get_db)) -> DemoStatus:
    return get_demo_status(db)


@router.get("/demo/scenarios", response_model=list[DemoScenario])
def read_demo_scenarios() -> list[DemoScenario]:
    return DEMO_SCENARIOS


@router.post(
    "/demo/seed",
    response_model=DemoSeedResult,
    dependencies=[Depends(block_public_demo_mutation)],
)
def seed_demo(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> DemoSeedResult:
    return seed_demo_data(db)
