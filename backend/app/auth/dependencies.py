from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import (
    demo_admin_context,
    demo_common_context,
    ensure_bootstrap_admin,
    user_context,
    user_from_token,
)
from app.core.config import get_settings
from app.db.session import get_db


bearer_scheme = HTTPBearer(auto_error=False)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserContext:
    settings = get_settings()
    if not settings.auth_enabled:
        if settings.public_demo_mode:
            return demo_common_context()
        return demo_admin_context()

    ensure_bootstrap_admin(db)
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = user_from_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    return user_context(user)


def require_admin(current_user: UserContext = Depends(require_user)) -> UserContext:
    if current_user.role != "admin":
        detail = (
            "Admin actions are disabled in public demo mode."
            if get_settings().public_demo_mode
            else "Admin role required"
        )
        raise HTTPException(status_code=403, detail=detail)
    return current_user
