from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import (
    demo_admin_context,
    demo_common_context,
    ensure_bootstrap_admin,
    sync_supabase_user,
    user_context,
    user_from_token,
)
from app.auth.supabase import SupabaseTokenError, verify_supabase_jwt
from app.core.config import get_settings
from app.db.session import get_db
from app.models.anonymous_session import AnonymousSessionModel


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

    if settings.auth_provider == "legacy_local":
        if settings.app_env == "production":
            raise HTTPException(status_code=500, detail="Legacy local auth is disabled in production")
        ensure_bootstrap_admin(db)
        if credentials is None or not credentials.credentials:
            raise HTTPException(status_code=401, detail="Authentication required")

        user = user_from_token(db, credentials.credentials)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        context = user_context(user)
    elif settings.auth_provider == "supabase":
        if credentials is None or not credentials.credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            claims = verify_supabase_jwt(credentials.credentials, settings)
        except SupabaseTokenError:
            raise HTTPException(status_code=401, detail="Invalid authentication token") from None
        try:
            user = sync_supabase_user(db, claims)
        except ValueError:
            raise HTTPException(status_code=403, detail="Account cannot be synchronized") from None
        if (
            settings.admin_mfa_required
            and user.platform_role == "admin"
            and claims.raw.get("aal") != "aal2"
        ):
            raise HTTPException(status_code=403, detail="Administrator MFA required")
        context = user_context(user)
    else:
        raise HTTPException(status_code=500, detail="Unsupported authentication provider")

    if not context.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    if settings.require_verified_email and not context.email_verified:
        raise HTTPException(status_code=403, detail="Verified email required")
    return context


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserContext | None:
    try:
        return require_user(credentials=credentials, db=db)
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise


def require_actor(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserContext:
    settings = get_settings()
    if settings.auth_enabled:
        user = optional_user(credentials=credentials, db=db)
        if user is not None:
            return user
    elif not settings.public_demo_mode:
        return demo_admin_context()

    if settings.public_demo_mode:
        return anonymous_context(request, response, db)

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return require_user(credentials=credentials, db=db)


def require_admin(current_user: UserContext = Depends(require_user)) -> UserContext:
    if not current_user.is_admin:
        detail = (
            "Admin actions are disabled in public demo mode."
            if get_settings().public_demo_mode
            else "Admin role required"
        )
        raise HTTPException(status_code=403, detail=detail)
    return current_user


def require_authenticated_user(current_user: UserContext = Depends(require_user)) -> UserContext:
    """Require a real authenticated/local-development user for durable mutations.

    This preserves Phase 15 public-demo behavior when authentication is disabled
    while allowing authenticated users to coexist with anonymous visitors in the
    Phase 16 hybrid deployment mode.
    """

    settings = get_settings()
    if settings.public_demo_mode and not settings.auth_enabled:
        raise HTTPException(
            status_code=403,
            detail="This mutation is disabled for anonymous public demo visitors.",
        )
    if not current_user.auth_enabled and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Authentication required")
    return current_user


def anonymous_context(request: Request, response: Response, db: Session) -> UserContext:
    settings = get_settings()
    now = datetime.now(UTC)
    cookie_name = settings.anonymous_session_cookie_name
    session_id = request.cookies.get(cookie_name, "")
    record = None
    if session_id:
        record = db.execute(
            select(AnonymousSessionModel)
            .where(AnonymousSessionModel.id == session_id)
            .where(AnonymousSessionModel.status == "active")
            .where(AnonymousSessionModel.expires_at > now)
        ).scalars().first()
    if record is None:
        session_id = f"anon_{token_urlsafe(32)}"
        record = AnonymousSessionModel(
            id=session_id,
            status="active",
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=settings.anonymous_retention_hours),
        )
        db.add(record)
    else:
        record.last_seen_at = now
    db.commit()
    response.set_cookie(
        key=cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        max_age=settings.anonymous_retention_hours * 3600,
    )
    context = demo_common_context()
    context.anonymous_session_id = session_id
    return context
