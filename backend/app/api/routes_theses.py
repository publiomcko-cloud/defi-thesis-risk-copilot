from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.theses.schemas import ThesisCreateRequest, ThesisResponse, ThesesResponse, ThesisUpdateRequest
from app.theses.service import create_thesis, delete_thesis, get_thesis, list_theses, update_thesis

router = APIRouter(tags=["theses"])


@router.get("/theses", response_model=ThesesResponse)
def get_theses(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesesResponse:
    return ThesesResponse(items=list_theses(db, actor))


@router.post("/theses", response_model=ThesisResponse)
def post_thesis(
    request: ThesisCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return create_thesis(db, actor, request)


@router.get("/theses/{thesis_id}", response_model=ThesisResponse)
def get_thesis_route(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return get_thesis(db, actor, thesis_id)


@router.patch("/theses/{thesis_id}", response_model=ThesisResponse)
def patch_thesis(
    thesis_id: str,
    request: ThesisUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return update_thesis(db, actor, thesis_id, request)


@router.delete("/theses/{thesis_id}", response_model=ThesisResponse)
def delete_thesis_route(
    thesis_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ThesisResponse:
    return delete_thesis(db, actor, thesis_id)
