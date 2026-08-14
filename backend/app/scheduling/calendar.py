from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException


CADENCE_SECONDS = {
    "hourly": 60 * 60,
    "six_hourly": 6 * 60 * 60,
}
CALENDAR_CADENCES = {"daily": 1, "weekly": 7}


def get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="timezone must be a valid IANA timezone") from exc


def next_due_after(current: datetime, cadence: str, timezone_name: str) -> datetime:
    """Advance one schedule interval without losing DST wall-clock intent.

    Short intervals use elapsed UTC time so an hourly schedule executes both
    real hours during a backward transition. Daily and weekly schedules retain
    their local wall-clock time, normalizing spring-forward imaginary times to
    the first valid local time after the transition.
    """

    current_utc = _as_utc(current)
    if cadence in CADENCE_SECONDS:
        return current_utc + timedelta(seconds=CADENCE_SECONDS[cadence])
    timezone = get_timezone(timezone_name)
    local = current_utc.astimezone(timezone)
    days = CALENDAR_CADENCES.get(cadence)
    if days is None:
        raise HTTPException(status_code=422, detail="Unsupported schedule cadence")
    return _normalize_local(local + timedelta(days=days), timezone)


def initial_due_after(now: datetime, cadence: str, timezone_name: str) -> datetime:
    """Use the creation instant as the user-visible cadence anchor."""

    get_timezone(timezone_name)
    return next_due_after(_as_utc(now), cadence, timezone_name)


def latest_due_not_after(first_due: datetime, cadence: str, timezone_name: str, now: datetime) -> tuple[datetime, datetime, bool]:
    """Return the coalesced occurrence and the first future due instant."""

    now_utc = _as_utc(now)
    due = _as_utc(first_due)
    coalesced = False
    # A disabled schedule can be stale for a long time. This loop is bounded to
    # avoid making a dispatcher claim unbounded; the fallback safely resets to
    # the next interval after now rather than replaying arbitrary old work.
    for _ in range(4096):
        following = next_due_after(due, cadence, timezone_name)
        if following > now_utc:
            return due, following, coalesced
        due = following
        coalesced = True
    return due, initial_due_after(now_utc, cadence, timezone_name), True


def first_due_after(now: datetime, cadence: str, timezone_name: str, starting_at: datetime) -> datetime:
    """Advance an existing schedule to the first future instant."""

    if _as_utc(starting_at) > _as_utc(now):
        return _as_utc(starting_at)
    _latest, next_due, _coalesced = latest_due_not_after(starting_at, cadence, timezone_name, now)
    return next_due


def _normalize_local(candidate: datetime, timezone: ZoneInfo) -> datetime:
    normalized = candidate.astimezone(UTC).astimezone(timezone)
    if normalized.replace(tzinfo=None) != candidate.replace(tzinfo=None):
        # `candidate` was an imaginary spring-forward time. The UTC round trip
        # chooses the first real local instant after the skipped wall-clock gap.
        return normalized.astimezone(UTC)
    return candidate.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
