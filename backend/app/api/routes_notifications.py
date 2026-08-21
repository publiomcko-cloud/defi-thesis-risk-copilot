from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.notifications.schemas import (
    NotificationActionResponse,
    NotificationMarkAllReadResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationsResponse,
    NotificationUnreadCountResponse,
)
from app.notifications.service import (
    get_notification,
    get_or_create_preferences,
    list_notifications,
    mark_all_read,
    mark_notification,
    notification_response,
    preference_response,
    unread_count,
    update_preferences,
)


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsResponse)
def read_notifications(
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = None,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationsResponse:
    records, next_cursor = list_notifications(db, actor.id, limit=limit, cursor=cursor)
    return NotificationsResponse(items=[notification_response(record) for record in records], next_cursor=next_cursor)


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def read_unread_count(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationUnreadCountResponse:
    return NotificationUnreadCountResponse(unread_count=unread_count(db, actor.id))


@router.get("/preferences", response_model=NotificationPreferenceResponse)
def read_preferences(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationPreferenceResponse:
    return preference_response(get_or_create_preferences(db, actor.id))


@router.patch("/preferences", response_model=NotificationPreferenceResponse)
def patch_preferences(
    request: NotificationPreferenceUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationPreferenceResponse:
    return update_preferences(db, actor.id, request)


@router.get("/{notification_id}", response_model=NotificationActionResponse)
def read_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationActionResponse:
    return NotificationActionResponse(notification=notification_response(get_notification(db, actor.id, notification_id)))


@router.post("/{notification_id}/read", response_model=NotificationActionResponse)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationActionResponse:
    return NotificationActionResponse(notification=notification_response(mark_notification(db, actor.id, notification_id, read=True)))


@router.post("/{notification_id}/unread", response_model=NotificationActionResponse)
def mark_unread(
    notification_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationActionResponse:
    return NotificationActionResponse(notification=notification_response(mark_notification(db, actor.id, notification_id, read=False)))


@router.post("/mark-all-read", response_model=NotificationMarkAllReadResponse)
def mark_all_visible_read(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> NotificationMarkAllReadResponse:
    return NotificationMarkAllReadResponse(updated_count=mark_all_read(db, actor.id, limit=limit))
