from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AlertCandidate:
    alert_type: str
    severity: str
    title: str
    message: str
    trigger_value: float | None
    threshold_value: float | None
    metadata: dict[str, Any]


def evaluate_rules(
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
) -> tuple[list[AlertCandidate], list[str]]:
    candidates: list[AlertCandidate] = []
    evaluated: list[str] = []

    _evaluate_upper_threshold(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name="borrow_apy_above_threshold",
        field="borrow_apy",
        label="Borrow APY",
    )
    _evaluate_lower_threshold(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name="net_spread_below_threshold",
        field="net_spread_apy",
        label="Net spread",
    )
    _evaluate_upper_threshold(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name="liquidity_below_threshold",
        field="liquidity_usd",
        label="Liquidity",
        lower_is_bad=True,
    )
    _evaluate_maturity(candidates, evaluated, title, rules, snapshot)
    _evaluate_risk_score_changed(candidates, evaluated, title, rules, snapshot)
    _evaluate_missing_data_resolved(candidates, evaluated, title, rules, snapshot)
    _evaluate_boolean_event(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name="new_discovered_item_needs_review",
        field="new_discovered_item_needs_review",
        message="A newly discovered source item needs human review.",
    )
    _evaluate_boolean_event(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name="source_update_detected",
        field="source_update_detected",
        message="A watched source update was detected and should be reviewed.",
    )
    return candidates, evaluated


def _evaluate_upper_threshold(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
    rule_name: str,
    field: str,
    label: str,
    lower_is_bad: bool = False,
) -> None:
    threshold = _number(rules.get(rule_name))
    value = _number(snapshot.get(field))
    if threshold is None or value is None:
        return
    evaluated.append(rule_name)
    triggered = value < threshold if lower_is_bad else value > threshold
    if not triggered:
        return
    direction = "below" if lower_is_bad else "above"
    candidates.append(
        AlertCandidate(
            alert_type=rule_name,
            severity="warning",
            title=f"{label} {direction} threshold",
            message=(
                f"{title}: {label} value {value} is {direction} threshold {threshold}. "
                "This is an analytical alert only, not a trade instruction."
            ),
            trigger_value=value,
            threshold_value=threshold,
            metadata={"field": field},
        )
    )


def _evaluate_lower_threshold(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
    rule_name: str,
    field: str,
    label: str,
) -> None:
    _evaluate_upper_threshold(
        candidates,
        evaluated,
        title,
        rules,
        snapshot,
        rule_name,
        field,
        label,
        lower_is_bad=True,
    )


def _evaluate_maturity(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    threshold = _number(rules.get("maturity_date_approaching_days"))
    days = _number(snapshot.get("days_to_maturity"))
    if threshold is None or days is None:
        return
    evaluated.append("maturity_date_approaching")
    if days <= threshold:
        candidates.append(
            AlertCandidate(
                alert_type="maturity_date_approaching",
                severity="warning",
                title="Maturity date approaching",
                message=(
                    f"{title}: days to maturity {days} is within threshold {threshold}. "
                    "Review exit assumptions; this is not an instruction to transact."
                ),
                trigger_value=days,
                threshold_value=threshold,
                metadata={"field": "days_to_maturity"},
            )
        )


def _evaluate_risk_score_changed(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    if not rules.get("risk_score_changed"):
        return
    previous = _number(snapshot.get("previous_risk_score"))
    current = _number(snapshot.get("risk_score"))
    if previous is None or current is None:
        return
    evaluated.append("risk_score_changed")
    if previous != current:
        candidates.append(
            AlertCandidate(
                alert_type="risk_score_changed",
                severity="info",
                title="Risk score changed",
                message=(
                    f"{title}: risk score changed from {previous} to {current}. "
                    "Review the drivers before relying on the prior thesis."
                ),
                trigger_value=current,
                threshold_value=previous,
                metadata={"previous_risk_score": previous},
            )
        )


def _evaluate_missing_data_resolved(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    if not rules.get("missing_data_resolved"):
        return
    previous = int(_number(snapshot.get("previous_missing_data_count")) or 0)
    current = int(_number(snapshot.get("missing_data_count")) or 0)
    evaluated.append("missing_data_resolved")
    if previous > 0 and current < previous:
        candidates.append(
            AlertCandidate(
                alert_type="missing_data_resolved",
                severity="info",
                title="Missing data improved",
                message=(
                    f"{title}: missing-data count improved from {previous} to {current}. "
                    "Review updated data quality before changing assumptions."
                ),
                trigger_value=float(current),
                threshold_value=float(previous),
                metadata={"previous_missing_data_count": previous},
            )
        )


def _evaluate_boolean_event(
    candidates: list[AlertCandidate],
    evaluated: list[str],
    title: str,
    rules: dict[str, Any],
    snapshot: dict[str, Any],
    rule_name: str,
    field: str,
    message: str,
) -> None:
    if not rules.get(rule_name):
        return
    evaluated.append(rule_name)
    if snapshot.get(field) is True:
        candidates.append(
            AlertCandidate(
                alert_type=rule_name,
                severity="info",
                title=rule_name.replace("_", " ").title(),
                message=f"{title}: {message}",
                trigger_value=None,
                threshold_value=None,
                metadata={"field": field, "evaluated_at": datetime.now(UTC).isoformat()},
            )
        )


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
