import pytest

from app.core.config import get_settings
from app.llm.base import LLMRequest, LLMResponse
from app.llm.synthesis import synthesize_report
from app.risk.framework import RiskComponent, RiskScore
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import ReportResponse, ReportSection, SourceReference


class SuccessfulProvider:
    name = "test_provider"
    model = "test_model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            provider=self.name,
            model=self.model,
            text=(
                "{"
                '"executive_summary":"LLM educational summary that preserves uncertainty.",'
                '"sections":{'
                '"Strategy Mechanics":"LLM explains mechanics in clearer educational language."'
                "}"
                "}"
            ),
        )


class FailingProvider:
    name = "failing_provider"
    model = "failing_model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise TimeoutError("simulated timeout")


class TamperingProvider:
    name = "tampering_provider"
    model = "tampering_model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            provider=self.name,
            model=self.model,
            text=(
                "{"
                '"report_id":"hijacked",'
                '"risk_rating":"Conservative",'
                '"executive_summary":"Tampered summary.",'
                '"sections":{"Risk Rating":"Conservative with score 1."}'
                "}"
            ),
        )


class RiskTamperingProvider:
    name = "risk_tampering_provider"
    model = "risk_tampering_model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            provider=self.name,
            model=self.model,
            text=(
                "{"
                '"executive_summary":"Educational summary.",'
                '"sections":{"Risk Analysis":"Very Risky score 8, but fabricated risk facts."}'
                "}"
            ),
        )


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_llm_synthesis_disabled_keeps_deterministic_report(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "false")
    get_settings.cache_clear()
    base_report = _base_report()

    result = synthesize_report(
        base_report=base_report,
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=SuccessfulProvider(),
    )

    assert not result.used_llm
    assert result.report.executive_summary == base_report.executive_summary
    assert any("skipped or unavailable" in item for item in result.report.assumptions)


def test_llm_failure_falls_back_to_deterministic_report(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    base_report = _base_report()

    result = synthesize_report(
        base_report=base_report,
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=FailingProvider(),
    )

    assert not result.used_llm
    assert result.reason == "provider_failure"
    assert result.outcome == "provider_failure"
    assert result.report.executive_summary == base_report.executive_summary
    assert any("skipped or unavailable" in item for item in result.report.assumptions)


def test_llm_output_cannot_override_deterministic_fields(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    base_report = _base_report()

    result = synthesize_report(
        base_report=base_report,
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=SuccessfulProvider(),
    )

    assert result.used_llm
    assert result.report.report_id == base_report.report_id
    assert result.report.risk_rating == "Very Risky"
    assert result.report.protocols == ["pendle", "morpho"]
    assert result.report.missing_data == base_report.missing_data
    assert result.report.sources == base_report.sources
    assert result.report.disclaimer == base_report.disclaimer
    assert _section(result.report, "Risk Rating") == _section(base_report, "Risk Rating")
    assert _section(result.report, "Sources") == _section(base_report, "Sources")
    assert _section(result.report, "Disclaimer") == _section(base_report, "Disclaimer")
    assert _section(result.report, "Risk Analysis") == _section(base_report, "Risk Analysis")
    assert "LLM explains mechanics" in _section(result.report, "Strategy Mechanics")
    assert any("Optional LLM synthesis was used" in item for item in result.report.assumptions)


def test_llm_assumptions_report_used_or_skipped(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    used = synthesize_report(
        base_report=_base_report(),
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=SuccessfulProvider(),
    )

    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "false")
    get_settings.cache_clear()
    skipped = synthesize_report(
        base_report=_base_report(),
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=SuccessfulProvider(),
    )

    assert any("Optional LLM synthesis was used" in item for item in used.report.assumptions)
    assert any("Optional LLM synthesis was skipped" in item for item in skipped.report.assumptions)
    assert not any("without live LLM calls" in item for item in used.report.assumptions)
    assert not any("without live LLM calls" in item for item in skipped.report.assumptions)


def test_llm_tampering_output_falls_back_without_mutating_deterministic_report(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    base_report = _base_report()

    result = synthesize_report(
        base_report=base_report,
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=TamperingProvider(),
    )

    assert result.reason == "validation_fallback"
    assert result.validation_result == "schema_invalid"
    assert result.report == base_report.model_copy(
        update={
            "assumptions": [
                *base_report.assumptions,
                "Optional LLM synthesis was skipped or unavailable; deterministic report template wording was used.",
            ]
        }
    )


def test_llm_cannot_rewrite_deterministic_risk_analysis(monkeypatch) -> None:
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    base_report = _base_report()

    result = synthesize_report(
        base_report=base_report,
        retrieved_context=[],
        market_data=_market_data(),
        risk_score=_risk_score(),
        provider=RiskTamperingProvider(),
    )

    assert result.outcome == "validation_fallback"
    assert result.validation_result == "schema_invalid"
    assert _section(result.report, "Risk Analysis") == _section(base_report, "Risk Analysis")


def _base_report() -> ReportResponse:
    disclaimer = (
        "This report is for research and educational purposes only. "
        "It does not execute trades, connect wallets, custody funds, or provide personalized financial advice."
    )
    return ReportResponse(
        report_id="report_test",
        risk_rating="Very Risky",
        executive_summary="Deterministic summary.",
        strategy_description="Analyze a Pendle PT strategy using Morpho borrow.",
        protocols=["pendle", "morpho"],
        assumptions=[
            "Controlled workflow uses local curated RAG retrieval. Optional LLM synthesis may enrich explanatory wording only when enabled."
        ],
        missing_data=["Liquidation buffer calculation"],
        sections=[
            ReportSection(title="Strategy Description", content="Analyze a Pendle PT strategy using Morpho borrow."),
            ReportSection(title="Protocols Involved", content="pendle, morpho"),
            ReportSection(title="Strategy Mechanics", content="Deterministic mechanics."),
            ReportSection(title="Yield Source", content="Deterministic yield source."),
            ReportSection(title="Market Data Summary", content="Deterministic market data."),
            ReportSection(title="Key Assumptions", content="Deterministic assumptions."),
            ReportSection(title="Risk Analysis", content="Deterministic risk analysis."),
            ReportSection(title="Stress Scenarios", content="Deterministic stress scenarios."),
            ReportSection(title="Simulation Summary", content="Deterministic simulation summary."),
            ReportSection(title="Exit Plan", content="Deterministic exit plan."),
            ReportSection(title="Monitoring Checklist", content="Deterministic checklist."),
            ReportSection(title="Risk Rating", content="Very Risky with score 8 and low confidence."),
            ReportSection(title="Missing Data and Uncertainty", content="- Liquidation buffer calculation"),
            ReportSection(title="Sources", content="- Risk framework (docs/risk_framework.md)"),
            ReportSection(title="Disclaimer", content=disclaimer),
        ],
        sources=[
            SourceReference(
                title="Risk framework",
                source_type="internal_doc",
                url="docs/risk_framework.md",
            )
        ],
        disclaimer=disclaimer,
    )


def _risk_score() -> RiskScore:
    return RiskScore(
        score=8,
        rating="Very Risky",
        components=[
            RiskComponent(
                category="liquidation_risk",
                points=1,
                reason="Borrowing creates liquidation risk.",
            )
        ],
        confidence="low",
        main_risk_drivers=["liquidation_risk"],
    )


def _market_data() -> MarketDataResponse:
    return MarketDataResponse(
        status="partial",
        source="aggregated_market_data",
        data={"adapters": []},
        missing_fields=["morpho.borrow_apy"],
        assumptions=["Manual inputs are unverified."],
    )


def _section(report: ReportResponse, title: str) -> str:
    return next(section.content for section in report.sections if section.title == title)
