from pydantic import BaseModel


class DemoScenario(BaseModel):
    id: str
    title: str
    summary: str
    primary_path: str
    report_id: str | None = None
    tags: list[str]
    safety_note: str = (
        "Educational demo only. No wallet connection, custody, trade execution, "
        "or personalized recommendation is involved."
    )


DEMO_SCENARIOS = [
    DemoScenario(
        id="pendle_pt_loop",
        title="Pendle PT + Lending Loop",
        summary=(
            "Synthetic Pendle fixed-yield position financed with Morpho/Aave-style "
            "borrowing to show deterministic risk scoring, missing data, stress "
            "scenarios, and monitoring checklists."
        ),
        primary_path="/reports/demo_report_pendle_pt_loop",
        report_id="demo_report_pendle_pt_loop",
        tags=["analysis", "pendle", "morpho", "risk-scoring"],
    ),
    DemoScenario(
        id="discovery_to_rag",
        title="Discovery to Human-Approved RAG",
        summary=(
            "Demo discovered source moves through evaluation, review, approval, "
            "and explicit knowledge-base ingestion."
        ),
        primary_path="/review",
        report_id="demo_report_discovery_to_rag",
        tags=["discovery", "review", "rag"],
    ),
    DemoScenario(
        id="watchlist_alert",
        title="Watchlist Alert",
        summary=(
            "Rule-based watchlist item with an open alert for liquidity and borrow "
            "cost thresholds."
        ),
        primary_path="/watchlist",
        report_id="demo_report_watchlist_alert",
        tags=["watchlist", "alerts", "monitoring"],
    ),
    DemoScenario(
        id="options_volatility",
        title="Options and Volatility Analysis",
        summary=(
            "Educational ETH call option scenario with premium, breakeven, max loss, "
            "payoff table assumptions, and volatility caveats."
        ),
        primary_path="/options",
        report_id="demo_report_options_volatility",
        tags=["options", "volatility", "payoff"],
    ),
    DemoScenario(
        id="vast_dry_run",
        title="Vast.ai Dry-Run Provider",
        summary=(
            "Admin-only dry-run model session showing lifecycle metadata without "
            "renting a real GPU."
        ),
        primary_path="/admin/vast",
        report_id="demo_report_vast_dry_run",
        tags=["admin", "vast", "dry-run"],
    ),
]
