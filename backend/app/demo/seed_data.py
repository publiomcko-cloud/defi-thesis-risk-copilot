from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.demo.scenarios import DEMO_SCENARIOS, DemoScenario
from app.models.alert_event import AlertEventModel
from app.models.analysis_request import AnalysisRequestModel
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.knowledge_base_ingestion import KnowledgeBaseIngestionModel
from app.models.report import ReportModel
from app.models.review_item import ReviewItemModel
from app.models.vast_session import VastSessionModel
from app.models.watchlist_item import WatchlistItemModel
from app.reports.markdown_export import render_markdown_report
from app.reports.renderer import make_section
from app.schemas.reports import ReportResponse, SourceReference

EXAMPLE_REPORTS_DIR = Path(__file__).resolve().parents[3] / "examples" / "reports"


class DemoSeedResult(BaseModel):
    status: str
    seeded: bool
    counts: dict[str, int]
    report_ids: list[str]
    scenario_ids: list[str]
    message: str


class DemoStatus(BaseModel):
    seeded: bool
    counts: dict[str, int]
    report_ids: list[str]
    scenarios: list[DemoScenario]


def seed_demo_data(db: Session, write_examples: bool | None = None) -> DemoSeedResult:
    settings = get_settings()
    should_write_examples = (not settings.public_demo_mode) if write_examples is None else write_examples
    now = datetime.now(UTC)
    reports = _demo_reports()
    for report in reports:
        _upsert_analysis_and_report(db, report, now)
    _upsert_discovery_flow(db, now)
    _upsert_watchlist(db, now)
    _upsert_vast_session(db, now)
    db.commit()
    if should_write_examples:
        write_example_reports(reports)
    status = get_demo_status(db)
    return DemoSeedResult(
        status="seeded",
        seeded=True,
        counts=status.counts,
        report_ids=status.report_ids,
        scenario_ids=[scenario.id for scenario in DEMO_SCENARIOS],
        message=(
            "Demo data seeded. All examples are synthetic, educational, non-advisory, "
            "and do not require wallets, paid APIs, or live Vast.ai rental."
        ),
    )


def get_demo_status(db: Session) -> DemoStatus:
    report_ids = [scenario.report_id for scenario in DEMO_SCENARIOS if scenario.report_id]
    counts = {
        "reports": _count_demo_reports(db),
        "discovered_items": _count_demo_discovered_items(db),
        "review_items": _count_demo_review_items(db),
        "knowledge_base_ingestions": _count_demo_ingestions(db),
        "watchlist_items": _count_demo_watchlist_items(db),
        "alert_events": _count_demo_alerts(db),
        "vast_sessions": _count_demo_vast_sessions(db),
    }
    return DemoStatus(
        seeded=counts["reports"] >= 4,
        counts=counts,
        report_ids=[report_id for report_id in report_ids if db.get(ReportModel, report_id) is not None],
        scenarios=DEMO_SCENARIOS,
    )


def write_example_reports(reports: list[ReportResponse] | None = None) -> list[Path]:
    EXAMPLE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = reports or _demo_reports()
    written = []
    filenames = {
        "demo_report_pendle_pt_loop": "pendle_pt_loop_report.md",
        "demo_report_discovery_to_rag": "discovery_to_rag_report.md",
        "demo_report_watchlist_alert": "watchlist_alert_report.md",
        "demo_report_options_volatility": "options_volatility_report.md",
        "demo_report_vast_dry_run": "vast_dry_run_report.md",
    }
    for report in reports:
        path = EXAMPLE_REPORTS_DIR / filenames[report.report_id]
        path.write_text(_example_markdown(report), encoding="utf-8")
        written.append(path)
    return written


def _upsert_analysis_and_report(db: Session, report: ReportResponse, now: datetime) -> None:
    analysis_id = f"demo_analysis_{report.report_id.removeprefix('demo_report_')}"
    analysis = db.get(AnalysisRequestModel, analysis_id)
    if analysis is None:
        analysis = AnalysisRequestModel(id=analysis_id, created_at=now)
        db.add(analysis)
    analysis.strategy_description = report.strategy_description
    analysis.protocols = report.protocols
    analysis.market_url = None
    analysis.manual_inputs_json = {"demo": True, "educational_only": True}
    analysis.analysis_depth = "standard"
    db.flush()

    record = db.get(ReportModel, report.report_id)
    markdown = render_markdown_report(report)
    if record is None:
        record = ReportModel(
            id=report.report_id,
            analysis_request_id=analysis_id,
            created_at=now,
            title=report.sections[0].content[:120],
            risk_rating=report.risk_rating,
            summary=report.executive_summary,
            report_markdown=markdown,
            report_json=report.model_dump(mode="json"),
        )
        db.add(record)
    else:
        record.analysis_request_id = analysis_id
        record.risk_rating = report.risk_rating
        record.summary = report.executive_summary
        record.report_markdown = markdown
        record.report_json = report.model_dump(mode="json")


def _upsert_discovery_flow(db: Session, now: datetime) -> None:
    discovered = _upsert(
        db,
        DiscoveredItemModel,
        "demo_disc_aurora_lend",
        discovery_key="demo:discovery:aurora-lend",
        source="demo",
        source_type="documentation",
        title="Demo Aurora Lend documentation",
        url="https://example.com/demo/aurora-lend-docs",
        protocol="aurora-lend-demo",
        chain="ethereum",
        asset=None,
        market_identifier="demo:aurora-lend",
        discovered_at=now,
        last_seen_at=now,
        raw_payload={
            "demo": True,
            "scenario": "discovery_to_rag",
            "source_quality_notes": ["Synthetic demo source", "Human approval required before trust"],
        },
        status="approved_for_rag",
    )
    db.flush()
    evaluation = _upsert(
        db,
        EvaluationResultModel,
        "demo_eval_aurora_lend",
        discovered_item_id=discovered.id,
        report_id="demo_report_discovery_to_rag",
        risk_rating="Moderate",
        risk_score=5,
        confidence="medium",
        risk_summary="Demo source has plausible documentation but missing audit recency and oracle details.",
        missing_data_json=["audit recency", "oracle implementation", "liquidity depth"],
        sources_json=[{"title": "Demo Aurora Lend docs", "url": discovered.url, "demo": True}],
        report_json={"demo": True, "labels": "deterministic-rule-demo"},
        created_at=now,
    )
    db.flush()
    _upsert(
        db,
        ReviewItemModel,
        "demo_review_aurora_lend",
        discovered_item_id=discovered.id,
        evaluation_result_id=evaluation.id,
        status="approved_for_rag",
        reviewer_notes="Demo reviewer approved this synthetic source for RAG ingestion.",
        prepared_for_rag=True,
        created_at=now,
        updated_at=now,
    )
    db.flush()
    _upsert(
        db,
        KnowledgeBaseIngestionModel,
        "demo_kbi_aurora_lend",
        review_item_id="demo_review_aurora_lend",
        generated_markdown_path="knowledge_base/discovered/demo_aurora_lend.md",
        ingested_at=now,
        ingested_by="demo_seed",
        source_url=discovered.url,
        protocol=discovered.protocol,
        status="ingested",
    )


def _upsert_watchlist(db: Session, now: datetime) -> None:
    _upsert(
        db,
        WatchlistItemModel,
        "demo_watch_pendle_loop",
        item_type="strategy",
        title="Demo Pendle PT loop monitor",
        protocol="pendle",
        market_identifier="demo:pendle-pt-loop",
        source_url="https://example.com/demo/pendle-loop",
        rules_json={
            "borrow_apy_above_threshold": 0.08,
            "net_spread_below_threshold": 0.02,
            "liquidity_below_threshold": 500000,
            "demo": True,
        },
        snapshot_json={
            "borrow_apy": 0.095,
            "net_spread_apy": 0.012,
            "liquidity_usd": 375000,
            "demo": True,
        },
        enabled=True,
        created_at=now,
        last_evaluated_at=now,
    )
    db.flush()
    _upsert(
        db,
        AlertEventModel,
        "demo_alert_pendle_liquidity",
        watchlist_item_id="demo_watch_pendle_loop",
        alert_type="liquidity_below_threshold",
        severity="warning",
        title="Demo liquidity threshold breached",
        message="Synthetic demo liquidity is below the configured monitoring threshold.",
        trigger_value=375000,
        threshold_value=500000,
        status="open",
        metadata_json={"demo": True, "scenario": "watchlist_alert"},
        created_at=now,
        updated_at=now,
    )


def _upsert_vast_session(db: Session, now: datetime) -> None:
    _upsert(
        db,
        VastSessionModel,
        "demo_vast_dry_run",
        status="destroyed",
        provider="vast_ai",
        vast_instance_id="dry_instance_demo",
        vast_contract_id="dry_contract_demo",
        offer_id="dry_offer_demo",
        model="demo-dry-run-model",
        image="demo/openai-compatible-server:dry-run",
        gpu_name="RTX_4090",
        hourly_cost_usd=0.0,
        max_runtime_minutes=30,
        container_port=8000,
        public_endpoint_url="http://dry-run-vast.local:8000",
        health_status="healthy",
        last_error=None,
        created_by="demo_seed",
        created_at=now,
        ready_at=now,
        last_used_at=now,
        destroyed_at=now,
        cleanup_attempted_at=now,
        metadata_json={"demo": True, "dry_run": True, "no_real_rental": True},
    )


def _demo_reports() -> list[ReportResponse]:
    return [
        _report(
            "demo_report_pendle_pt_loop",
            "Moderate",
            "Synthetic Pendle PT loop shows attractive fixed-yield mechanics but meaningful borrow, liquidity, oracle, and liquidation sensitivity.",
            "Analyze a synthetic Pendle PT position financed with Morpho/Aave-style borrowing.",
            ["pendle", "morpho", "aave"],
            ["live borrow APY", "oracle configuration", "exit liquidity during stress"],
            "Score 5/10. Main drivers are leverage, borrow-rate sensitivity, PT liquidity, oracle assumptions, and maturity mismatch.",
        ),
        _report(
            "demo_report_discovery_to_rag",
            "Moderate",
            "Demo discovered protocol documentation is routed through review before becoming trusted RAG context.",
            "Evaluate a newly discovered synthetic lending protocol source before knowledge-base ingestion.",
            ["aurora-lend-demo"],
            ["audit recency", "oracle implementation", "liquidity depth"],
            "Score 5/10. Human approval is required because documentation alone does not establish production safety.",
        ),
        _report(
            "demo_report_watchlist_alert",
            "Aggressive",
            "Demo watchlist alert highlights how threshold breaches can be surfaced without trading automation.",
            "Monitor a synthetic Pendle PT loop for liquidity and borrow-cost deterioration.",
            ["pendle", "morpho"],
            ["real-time liquidity", "market depth", "borrow utilization"],
            "Score 7/10. Alert drivers are low liquidity, narrow net spread, and elevated borrow APY.",
        ),
        _report(
            "demo_report_options_volatility",
            "Very Risky",
            "Educational ETH call option scenario demonstrates payoff asymmetry, premium at risk, and volatility assumptions.",
            "Analyze a synthetic ETH call option payoff and volatility thesis.",
            ["options-demo"],
            ["real option chain", "implied volatility surface", "settlement venue risk"],
            "Score 8/10. Main drivers are total premium at risk, volatility uncertainty, spread/slippage, and expiry timing.",
        ),
        _report(
            "demo_report_vast_dry_run",
            "Moderate",
            "Vast.ai dry-run demo shows admin-only lifecycle controls without renting real GPU infrastructure.",
            "Demonstrate an admin-only Vast.ai dry-run model session and cleanup workflow.",
            ["vast-ai-demo"],
            ["real provider credentials", "live offer availability", "container health in production"],
            "Score 4/10 for demo infrastructure. Real rental remains disabled until explicit admin approval and production hardening.",
        ),
    ]


def _report(
    report_id: str,
    risk_rating: str,
    summary: str,
    strategy: str,
    protocols: list[str],
    missing_data: list[str],
    risk_analysis: str,
) -> ReportResponse:
    assumptions = [
        "Demo data is synthetic and deterministic.",
        "No wallet, custody, transaction signing, or trade execution is involved.",
        "Optional LLM synthesis is not required to reproduce this demo.",
    ]
    sources = [
        SourceReference(
            title="Local demo seed data",
            source_type="demo",
            url="https://example.com/defi-risk-copilot-demo",
            protocol=protocols[0] if protocols else None,
        )
    ]
    sections = [
        make_section("Strategy Description", strategy),
        make_section("Protocols Involved", ", ".join(protocols)),
        make_section("Strategy Mechanics", "Synthetic inputs demonstrate the workflow without using live positions or paid APIs."),
        make_section("Yield Source", "Demo yield assumptions come from fixed synthetic values, not investment recommendations."),
        make_section("Market Data Summary", "Market values are stable demo assumptions designed for reproducible review."),
        make_section("Key Assumptions", "; ".join(assumptions)),
        make_section("Risk Analysis", risk_analysis),
        make_section("Stress Scenarios", "Stress examples include borrow-rate shocks, liquidity drawdowns, and adverse exit conditions."),
        make_section("Simulation Summary", "Use the simulator page to reproduce deterministic scenario outputs with the provided assumptions."),
        make_section("Exit Plan", "Demo exit planning emphasizes monitoring and uncertainty, not instructions to trade."),
        make_section("Monitoring Checklist", "Track borrow APY, liquidity depth, oracle status, maturity dates, and missing data."),
        make_section("Risk Rating", f"{risk_rating}. Deterministic scoring remains the source of truth."),
        make_section("Missing Data and Uncertainty", ", ".join(missing_data)),
        make_section("Sources", "Local demo seed data and curated project documentation."),
        make_section("Disclaimer", _disclaimer()),
    ]
    return ReportResponse(
        report_id=report_id,
        status="completed",
        risk_rating=risk_rating,  # type: ignore[arg-type]
        executive_summary=summary,
        strategy_description=strategy,
        protocols=protocols,
        assumptions=assumptions,
        missing_data=missing_data,
        sections=sections,
        sources=sources,
        disclaimer=_disclaimer(),
    )


def _example_markdown(report: ReportResponse) -> str:
    reproduce = (
        "## How to Reproduce Inside the App\n\n"
        "1. Start the local stack with `docker compose up -d --build`.\n"
        "2. Run `POST /api/demo/seed` or use the Demo page seed action.\n"
        f"3. Open `/reports/{report.report_id}` or use `/demo` scenario links.\n"
    )
    limitations = (
        "## Limitations\n\n"
        "- Demo values are synthetic and may not reflect live markets.\n"
        "- Reports are educational research artifacts, not recommendations.\n"
        "- No wallet connection, custody, transaction signing, or trade execution exists.\n"
    )
    return f"{render_markdown_report(report)}\n\n{limitations}\n\n{reproduce}\n\n## Non-Advisory Disclaimer\n\n{_disclaimer()}\n"


def _disclaimer() -> str:
    return (
        "This demo is for educational research only. It is not financial, investment, legal, or tax advice. "
        "It does not recommend buying, selling, borrowing, lending, or entering any position."
    )


def _upsert(db: Session, model_class, record_id: str, **values):
    record = db.get(model_class, record_id)
    if record is None:
        record = model_class(id=record_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    return record


def _count_demo_reports(db: Session) -> int:
    return len(db.execute(select(ReportModel).where(ReportModel.id.like("demo_report_%"))).scalars().all())


def _count_demo_discovered_items(db: Session) -> int:
    return len(db.execute(select(DiscoveredItemModel).where(DiscoveredItemModel.source == "demo")).scalars().all())


def _count_demo_review_items(db: Session) -> int:
    return 1 if db.get(ReviewItemModel, "demo_review_aurora_lend") else 0


def _count_demo_ingestions(db: Session) -> int:
    return len(db.execute(select(KnowledgeBaseIngestionModel).where(KnowledgeBaseIngestionModel.ingested_by == "demo_seed")).scalars().all())


def _count_demo_watchlist_items(db: Session) -> int:
    return len(db.execute(select(WatchlistItemModel).where(WatchlistItemModel.id.like("demo_watch_%"))).scalars().all())


def _count_demo_alerts(db: Session) -> int:
    return len(db.execute(select(AlertEventModel).where(AlertEventModel.id.like("demo_alert_%"))).scalars().all())


def _count_demo_vast_sessions(db: Session) -> int:
    return len(db.execute(select(VastSessionModel).where(VastSessionModel.id.like("demo_vast_%"))).scalars().all())
