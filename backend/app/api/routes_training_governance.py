from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.core.config import get_settings
from app.db.session import get_db
from app.training_governance.schemas import (
    SealTrainingDatasetRequest,
    SubmitTrainingRunRequest,
    TrainingGovernanceResponse,
    TrainingManifestResponse,
    TrainingRunResponse,
)
from app.training_governance.service import (
    governance_snapshot,
    manifest_response,
    run_response,
    seal_checked_in_manifest,
    submit_training_run,
)


router = APIRouter(prefix="/admin/training-governance", tags=["training-governance"])


@router.get("", response_model=TrainingGovernanceResponse)
def read_training_governance(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> TrainingGovernanceResponse:
    return governance_snapshot(db)


@router.post("/manifests/seal", response_model=TrainingManifestResponse, status_code=201)
def seal_training_manifest(
    payload: SealTrainingDatasetRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_admin),
) -> TrainingManifestResponse:
    _block_public_demo_mutation()
    manifest = seal_checked_in_manifest(db, actor, dataset_key=payload.dataset_key)
    db.commit()
    db.refresh(manifest)
    return manifest_response(manifest)


@router.post("/runs", response_model=TrainingRunResponse, status_code=202)
def create_training_run(
    payload: SubmitTrainingRunRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_admin),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> TrainingRunResponse:
    _block_public_demo_mutation()
    run, _ = submit_training_run(
        db,
        actor,
        dataset_key=payload.dataset_key,
        execution_mode=payload.execution_mode,
        idempotency_key=idempotency_key,
    )
    return run_response(db, run)


def _block_public_demo_mutation() -> None:
    settings = get_settings()
    if settings.public_demo_mode and not settings.auth_enabled:
        raise HTTPException(status_code=403, detail="Training governance changes are disabled in public demo mode.")
