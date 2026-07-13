from datetime import UTC, date, datetime


def bid_ask_spread(bid: float | None, ask: float | None) -> tuple[float | None, float | None]:
    if bid is None or ask is None:
        return None, None
    spread = max(ask - bid, 0)
    mid = (ask + bid) / 2
    spread_pct = spread / mid if mid else None
    return spread, spread_pct


def days_to_expiration(expiration_date: str | None) -> int | None:
    if not expiration_date:
        return None
    parsed = date.fromisoformat(expiration_date)
    return (parsed - datetime.now(UTC).date()).days


def volatility_summary(implied_volatility: float | None, volatility_thesis: str | None) -> str:
    if implied_volatility is None:
        return "Implied volatility was not provided, so volatility richness cannot be framed."
    thesis = volatility_thesis or "No explicit volatility thesis was provided."
    return (
        f"Implied volatility is {implied_volatility:.2%}. "
        f"Volatility thesis: {thesis} "
        "This frames sensitivity to volatility assumptions but does not forecast realized volatility."
    )
