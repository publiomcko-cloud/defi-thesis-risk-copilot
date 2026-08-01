from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import get_settings
from app.models.product_analytics import (
    PrivacyPreferenceDecisionModel,
    PrivacyPreferenceModel,
    ProductAnalyticsEventModel,
)
from app.models.user import UserModel
from app.product_analytics.registry import (
    ANALYTICS_SCHEMA_VERSION,
    PURPOSE_PRODUCT_IMPROVEMENT,
    validate_event_metadata,
)
from app.product_analytics.schemas import PrivacyPreferenceResponse, PrivacyPreferenceUpdateResponse


logger = logging.getLogger(__name__)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def get_privacy_preference(db: Session, actor: UserContext) -> PrivacyPreferenceResponse:
    settings = get_settings()
    preference = db.execute(
        select(PrivacyPreferenceModel)
        .where(PrivacyPreferenceModel.user_id == actor.id)
        .where(PrivacyPreferenceModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
    ).scalars().one_or_none()
    matches_policy = bool(
        preference is not None
        and preference.enabled
        and preference.policy_version == settings.product_analytics_policy_version
    )
    return PrivacyPreferenceResponse(
        purpose=PURPOSE_PRODUCT_IMPROVEMENT,
        enabled=matches_policy,
        policy_version=settings.product_analytics_policy_version,
        collection_enabled=settings.product_analytics_enabled,
        requires_reconsent=bool(preference is not None and preference.enabled and not matches_policy),
        updated_at=preference.updated_at if preference is not None else None,
    )


def set_privacy_preference(
    db: Session,
    actor: UserContext,
    *,
    enabled: bool,
    idempotency_key: str | None,
) -> PrivacyPreferenceUpdateResponse:
    settings = get_settings()
    _lock_active_user(db, actor.id)
    if enabled and not settings.product_analytics_enabled:
        raise HTTPException(
            status_code=409,
            detail="Product analytics collection is unavailable for this deployment",
        )
    normalized_key = _decision_idempotency_key(actor.id, idempotency_key)
    existing = db.execute(
        select(PrivacyPreferenceDecisionModel)
        .where(PrivacyPreferenceDecisionModel.user_id == actor.id)
        .where(PrivacyPreferenceDecisionModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
        .where(PrivacyPreferenceDecisionModel.idempotency_key == normalized_key)
    ).scalars().one_or_none()
    if existing is not None:
        if _decision_enables(existing.decision) != enabled:
            raise HTTPException(status_code=409, detail="Idempotency-Key was already used for another decision")
        return PrivacyPreferenceUpdateResponse(
            preference=get_privacy_preference(db, actor),
            decision=existing.decision,
            duplicate=True,
        )

    preference = db.execute(
        select(PrivacyPreferenceModel)
        .where(PrivacyPreferenceModel.user_id == actor.id)
        .where(PrivacyPreferenceModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
        .with_for_update()
    ).scalars().one_or_none()
    now = datetime.now(UTC)
    decision_name = "grant" if enabled else "withdraw" if preference is not None and preference.enabled else "deny"
    decision = PrivacyPreferenceDecisionModel(
        id=f"ppd_{uuid4().hex[:24]}",
        user_id=actor.id,
        purpose=PURPOSE_PRODUCT_IMPROVEMENT,
        decision=decision_name,
        policy_version=settings.product_analytics_policy_version,
        previous_decision_id=preference.latest_decision_id if preference is not None else None,
        idempotency_key=normalized_key,
        source="account_ui",
        occurred_at=now,
        created_at=now,
    )
    db.add(decision)
    db.flush()
    if preference is None:
        preference = PrivacyPreferenceModel(
            id=f"ppr_{uuid4().hex[:24]}",
            user_id=actor.id,
            purpose=PURPOSE_PRODUCT_IMPROVEMENT,
            enabled=enabled,
            policy_version=settings.product_analytics_policy_version,
            latest_decision_id=decision.id,
            updated_at=now,
        )
        db.add(preference)
    else:
        preference.enabled = enabled
        preference.policy_version = settings.product_analytics_policy_version
        preference.latest_decision_id = decision.id
        preference.updated_at = now
    if not enabled:
        db.execute(
            delete(ProductAnalyticsEventModel)
            .where(ProductAnalyticsEventModel.owner_user_id == actor.id)
            .where(ProductAnalyticsEventModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
        )
    record_audit_event(
        db,
        actor.id,
        f"privacy.analytics_{decision_name}",
        "privacy_preference",
        metadata={
            "purpose": PURPOSE_PRODUCT_IMPROVEMENT,
            "policy_version": settings.product_analytics_policy_version,
        },
        commit=False,
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.execute(
            select(PrivacyPreferenceDecisionModel)
            .where(PrivacyPreferenceDecisionModel.user_id == actor.id)
            .where(PrivacyPreferenceDecisionModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
            .where(PrivacyPreferenceDecisionModel.idempotency_key == normalized_key)
        ).scalars().one_or_none()
        if duplicate is None or _decision_enables(duplicate.decision) != enabled:
            raise
        return PrivacyPreferenceUpdateResponse(
            preference=get_privacy_preference(db, actor),
            decision=duplicate.decision,
            duplicate=True,
        )
    return PrivacyPreferenceUpdateResponse(
        preference=get_privacy_preference(db, actor),
        decision=decision_name,
        duplicate=False,
    )


def record_product_event(
    db: Session,
    *,
    owner_user_id: str,
    event_name: str,
    metadata: dict,
    source_boundary: str,
    occurred_at: datetime | None = None,
) -> bool:
    normalized = validate_event_metadata(event_name, metadata)
    if not source_boundary or len(source_boundary) > 256:
        raise ValueError("Product analytics source boundary is invalid")
    settings = get_settings()
    if not settings.product_analytics_enabled:
        return False
    owner = db.execute(
        select(UserModel).where(UserModel.id == owner_user_id).with_for_update()
    ).scalars().one_or_none()
    if owner is None or not owner.is_active or owner.account_status != "active" or owner.deleted_at is not None:
        return False
    preference = db.execute(
        select(PrivacyPreferenceModel)
        .where(PrivacyPreferenceModel.user_id == owner_user_id)
        .where(PrivacyPreferenceModel.purpose == PURPOSE_PRODUCT_IMPROVEMENT)
        .with_for_update()
    ).scalars().one_or_none()
    if (
        preference is None
        or not preference.enabled
        or preference.policy_version != settings.product_analytics_policy_version
    ):
        return False
    decision = db.get(PrivacyPreferenceDecisionModel, preference.latest_decision_id)
    if decision is None or decision.decision != "grant" or decision.policy_version != preference.policy_version:
        return False

    event_key = _event_key(owner_user_id, event_name, source_boundary)
    if db.execute(
        select(ProductAnalyticsEventModel.id).where(ProductAnalyticsEventModel.event_key == event_key)
    ).scalar_one_or_none() is not None:
        return False
    received_at = datetime.now(UTC)
    actor_class = normalized.pop("actor_class")
    db.add(
        ProductAnalyticsEventModel(
            id=f"pae_{uuid4().hex[:24]}",
            event_name=event_name,
            schema_version=ANALYTICS_SCHEMA_VERSION,
            purpose=PURPOSE_PRODUCT_IMPROVEMENT,
            owner_user_id=owner_user_id,
            actor_class=actor_class,
            dimensions_json=normalized,
            event_key=event_key,
            policy_version=preference.policy_version,
            decision_id=decision.id,
            occurred_at=occurred_at or received_at,
            received_at=received_at,
            expires_at=received_at + timedelta(days=settings.product_analytics_retention_days),
        )
    )
    db.commit()
    return True


def emit_product_event_safely(db: Session, **kwargs) -> bool:
    try:
        return record_product_event(db, **kwargs)
    except Exception:
        db.rollback()
        logger.warning(
            "Optional product analytics event was dropped",
            extra={"event": "product_analytics.event_dropped", "analytics_event_name": kwargs.get("event_name")},
        )
        return False


def dispose_product_analytics_for_account(db: Session, user_id: str) -> dict[str, int]:
    events = db.execute(
        delete(ProductAnalyticsEventModel).where(ProductAnalyticsEventModel.owner_user_id == user_id)
    ).rowcount or 0
    preferences = db.execute(
        delete(PrivacyPreferenceModel).where(PrivacyPreferenceModel.user_id == user_id)
    ).rowcount or 0
    return {"events": events, "preferences": preferences}


def _lock_active_user(db: Session, user_id: str) -> UserModel:
    user = db.execute(select(UserModel).where(UserModel.id == user_id).with_for_update()).scalars().one_or_none()
    if user is None or not user.is_active or user.account_status != "active" or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Account not found")
    return user


def _decision_idempotency_key(user_id: str, provided: str | None) -> str:
    candidate = provided.strip() if provided else f"server_{uuid4().hex}"
    if not IDEMPOTENCY_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Idempotency-Key format is invalid")
    digest = hashlib.sha256(f"phase20b-decision\0{user_id}\0{candidate}".encode("utf-8")).hexdigest()
    return f"idem_{digest}"


def _event_key(owner_user_id: str, event_name: str, source_boundary: str) -> str:
    digest = hashlib.sha256(
        f"phase20b-event\0{owner_user_id}\0{event_name}\0{source_boundary}".encode("utf-8")
    ).hexdigest()
    return f"pae_{digest}"


def _decision_enables(decision: str) -> bool:
    return decision == "grant"
