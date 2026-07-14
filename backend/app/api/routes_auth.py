from fastapi import APIRouter, Depends

from app.auth.dependencies import require_user
from app.auth.schemas import UserContext

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserContext)
def read_current_user(current_user: UserContext = Depends(require_user)) -> UserContext:
    return current_user
