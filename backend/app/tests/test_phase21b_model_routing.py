from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.llm.base import LLMRequest, LLMResponse
from app.llm.evaluation import (
    ModelEvaluationError,
    ensure_report_synthesis_evaluation_dataset,
    evaluate_report_synthesis_candidate,
    promote_evaluation_route,
    rollback_route,
)
from app.llm.evaluation_data import report_synthesis_adversarial_dataset, report_synthesis_public_dataset
from app.llm.governance import ensure_report_synthesis_prompt_version, record_model_run_provenance
from app.llm.provenance import build_report_synthesis_candidate
from app.llm.routing import server_environment, resolve_report_synthesis_route
from app.llm.synthesis import synthesize_report
from app.models.model_governance import (
    ModelEvaluationCaseResultModel,
    ModelEvaluationDatasetModel,
    ModelEvaluationRunModel,
    ModelPromptVersionModel,
    ModelRegistryModel,
    ModelRouteAssignmentModel,
    ModelRouteTransitionModel,
    ModelRouteVersionModel,
)
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.schemas.analysis import AnalysisRequest


class SyntheticProvider:
    name = "synthetic_provider"
    model = "synthetic-model-v1"
    privacy_classification = "private_approved"

    def __init__(self, failure_case: str | None = None, model: str = "synthetic-model-v1") -> None:
        self.failure_case = failure_case
        self.model = model
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        failure_class = self.failure_case
        if failure_class and f"Expected failure class: {failure_class}." in request.prompt:
            if failure_class == "unsafe_language":
                return LLMResponse(
                    text='{"executive_summary":"You should buy this immediately.","sections":{}}',
                    provider=self.name,
                    model=self.model,
                )
            if failure_class == "provider_failure":
                raise TimeoutError("synthetic provider failure")
            immutable_title = {
                "risk_mutation": "Risk Analysis",
                "source_mutation": "Sources",
                "missing_data_suppression": "Missing Data and Uncertainty",
            }.get(failure_class)
            if immutable_title:
                return LLMResponse(
                    text=(
                        '{"executive_summary":"Synthetic summary.",'
                        f'"sections":{{"{immutable_title}":"forged"}}}}'
                    ),
                    provider=self.name,
                    model=self.model,
                )
            if failure_class == "unsupported_source_claim":
                return LLMResponse(
                    text=(
                        '{"executive_summary":"Synthetic summary.",'
                        '"sections":{"Strategy Mechanics":"See https://unsupported.example/claim."}}'
                    ),
                    provider=self.name,
                    model=self.model,
                )
            return LLMResponse(text="not json", provider=self.name, model=self.model)
        return LLMResponse(
            text=(
                '{"executive_summary":"Synthetic educational summary preserves uncertainty.",'
                '"sections":{"Strategy Mechanics":"Synthetic educational mechanics remain bounded."}}'
            ),
            provider=self.name,
            model=self.model,
            input_tokens=11,
            output_tokens=7,
            total_tokens=18,
        )


class PublicOnlyProvider(SyntheticProvider):
    privacy_classification = "public_only"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def routing_session(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LLM_SYNTHESIS_ENABLED", "true")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield Session
    finally:
        Base.metadata.drop_all(engine)


def test_public_dataset_is_versioned_immutable_and_contains_no_private_payload(routing_session) -> None:
    definition = report_synthesis_public_dataset()
    assert definition.dataset_id == "report_synthesis_public_v2"
    assert len(definition.cases) >= 13
    assert {case.category for case in definition.cases} >= {
        "valid_ordinary",
        "malformed_json",
        "missing_required_fields",
        "unexpected_fields",
        "deterministic_risk_mutation",
        "source_citation_mutation",
        "missing_data_suppression",
        "unsafe_trade_language",
        "instruction_like_retrieval",
        "unsupported_source_claim",
        "missing_source_honesty",
        "provider_failure",
        "empty_retrieval",
        "partial_retrieval",
    }
    assert all(case.retrieval_fixture and case.expected_result for case in definition.cases)
    assert {case.expected_failure_class for case in definition.cases if case.expected_failure_class} >= {
        "malformed_json",
        "risk_mutation",
        "source_mutation",
        "missing_data_suppression",
        "unsafe_language",
        "unsupported_source_claim",
        "provider_failure",
    }
    with routing_session() as db:
        dataset = ensure_report_synthesis_evaluation_dataset(db)
        db.commit()
        assert dataset.dataset_checksum == definition.checksum
        assert dataset.case_count == len(definition.cases)
        assert "prompt" not in str(dataset.__dict__).lower()
        dataset.dataset_version = "forged"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_evaluation_is_durable_redacted_and_requires_explicit_promotion(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-admin@example.test", role="admin"))
        run = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(), actor=operator)
        assert run.status == "completed"
        assert run.promotion_eligible is True
        expected_case_count = len(report_synthesis_public_dataset().cases) + len(report_synthesis_adversarial_dataset().cases)
        assert run.case_count == expected_case_count
        assert run.passed_case_count == expected_case_count
        assert run.token_observation_count == expected_case_count
        assert run.cost_observation_count == 0
        assert db.scalars(select(ModelRouteAssignmentModel)).all() == []
        case_rows = db.scalars(select(ModelEvaluationCaseResultModel).where(ModelEvaluationCaseResultModel.evaluation_run_id == run.id)).all()
        assert len(case_rows) == expected_case_count
        serialized = str(run.__dict__) + str(case_rows[0].__dict__)
        assert "Synthetic public strategy" not in serialized
        assert "api_key" not in serialized.lower()
        run.case_count = 1
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_failing_evaluation_cannot_promote_and_unknown_task_fails_closed(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-failed-admin@example.test", role="admin"))
        run = evaluate_report_synthesis_candidate(
            db,
            provider=SyntheticProvider(failure_case="malformed_json"),
            actor=operator,
        )
        assert run.status == "completed"
        assert run.promotion_eligible is False
        assert run.structured_output_valid_count == run.case_count - 1
        with pytest.raises(ModelEvaluationError, match="Passing completed"):
            promote_evaluation_route(db, evaluation_run_id=run.id, actor=operator)
        with pytest.raises(ValueError, match="Unknown model task"):
            evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(), actor=operator, task_key="browser_task")


@pytest.mark.parametrize(
    ("case_id", "failed_metric"),
    [
        ("risk_mutation", "deterministic_preserved_count"),
        ("source_mutation", "source_integrity_count"),
        ("unsupported_source_claim", "source_integrity_count"),
        ("missing_data_suppression", "missing_data_honesty_count"),
        ("unsafe_language", "unsafe_language_violation_count"),
        ("provider_failure", "provider_failure_count"),
    ],
)
def test_evaluation_hard_invariants_reject_mutation_unsafe_and_provider_failures(
    routing_session,
    case_id: str,
    failed_metric: str,
) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, f"phase21b-{case_id}@example.test", role="admin"))
        run = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(failure_case=case_id), actor=operator)
        assert run.promotion_eligible is False
        if failed_metric == "unsafe_language_violation_count":
            assert getattr(run, failed_metric) == 1
        elif failed_metric == "provider_failure_count":
            assert getattr(run, failed_metric) == 1
        else:
            assert getattr(run, failed_metric) == run.case_count - 1


def test_promoted_route_is_required_for_runtime_and_rollback_is_idempotent(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-route-admin@example.test", role="admin"))
        provider = SyntheticProvider()
        base, context, market, risk = _runtime_inputs()
        no_route = synthesize_report(base, context, market, risk, provider=provider, content_scope="public", db=db)
        assert no_route.used_llm is False
        assert no_route.fallback_reason == "no_promoted_route"

        run = evaluate_report_synthesis_candidate(db, provider=provider, actor=operator)
        assert db.scalars(select(ModelRouteAssignmentModel)).all() == []
        route = promote_evaluation_route(db, evaluation_run_id=run.id, actor=operator)
        resolved = synthesize_report(base, context, market, risk, provider=provider, content_scope="public", db=db)
        assert resolved.used_llm is True
        assert resolved.route_version_id == route.id
        assert resolved.evaluation_run_id == run.id

        assignment = rollback_route(db, route_version_id=route.id, actor=operator)
        assert assignment.active_route_version_id is None
        repeated = rollback_route(db, route_version_id=route.id, actor=operator)
        assert repeated.active_route_version_id is None
        assert len(db.scalars(select(ModelRouteTransitionModel)).all()) == 2
        after = synthesize_report(base, context, market, risk, provider=provider, content_scope="public", db=db)
        assert after.used_llm is False
        assert after.fallback_reason == "no_promoted_route"


def test_rollback_restores_the_previous_known_good_route(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-rollback-admin@example.test", role="admin"))
        first = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="synthetic-model-a"), actor=operator)
        route_a = promote_evaluation_route(db, evaluation_run_id=first.id, actor=operator)
        second = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="synthetic-model-b"), actor=operator)
        route_b = promote_evaluation_route(db, evaluation_run_id=second.id, actor=operator)
        assert route_b.previous_route_version_id == route_a.id
        assignment = rollback_route(db, route_version_id=route_b.id, actor=operator)
        assert assignment.active_route_version_id == route_a.id


@pytest.mark.parametrize("obsolete_authority", ["prompt", "policy"])
def test_rollback_clears_an_obsolete_previous_route(routing_session, obsolete_authority: str) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, f"phase21c-obsolete-{obsolete_authority}@example.test", role="admin"))
        first = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model=f"obsolete-{obsolete_authority}-a"), actor=operator)
        route_a = promote_evaluation_route(db, evaluation_run_id=first.id, actor=operator)
        second = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model=f"obsolete-{obsolete_authority}-b"), actor=operator)
        route_b = promote_evaluation_route(db, evaluation_run_id=second.id, actor=operator)

        if obsolete_authority == "prompt":
            current = ensure_report_synthesis_prompt_version(db)
            historical = ModelPromptVersionModel(
                id=f"prompt_phase21c_obsolete_{obsolete_authority}",
                task_key=current.task_key,
                task_version=current.task_version,
                prompt_version="report_synthesis.prompt.v2",
                output_schema_version=current.output_schema_version,
                safety_policy_version=current.safety_policy_version,
                prompt_checksum="f" * 64,
            )
            db.add(historical)
            db.flush()
            db.execute(
                ModelRouteVersionModel.__table__.update()
                .where(ModelRouteVersionModel.id == route_a.id)
                .values(prompt_version_id=historical.id)
            )
            db.execute(
                ModelEvaluationRunModel.__table__.update()
                .where(ModelEvaluationRunModel.id == first.id)
                .values(prompt_version_id=historical.id)
            )
        else:
            db.execute(
                ModelEvaluationRunModel.__table__.update()
                .where(ModelEvaluationRunModel.id == first.id)
                .values(policy_version="report_synthesis.promotion.v1", policy_checksum="e" * 64)
            )
        db.commit()

        assignment = rollback_route(db, route_version_id=route_b.id, actor=operator)
        assert assignment.active_route_version_id is None


def test_routed_synthesis_persists_exact_route_and_evaluation_provenance(routing_session) -> None:
    with routing_session() as db:
        operator_record = create_user(db, "phase21b-provenance-admin@example.test", role="admin")
        operator = user_context(operator_record)
        provider = SyntheticProvider()
        evaluation = evaluate_report_synthesis_candidate(db, provider=provider, actor=operator)
        route = promote_evaluation_route(db, evaluation_run_id=evaluation.id, actor=operator)
        base, context, market, risk = _runtime_inputs()
        base = base.model_copy(update={"report_id": "report_phase21b_provenance"})
        result = synthesize_report(base, context, market, risk, provider=provider, content_scope="private", db=db)
        db.add(
            AnalysisRequestModel(
                id="analysis_phase21b_provenance",
                strategy_description="Synthetic public strategy for provenance testing.",
                protocols=["synthetic"],
                manual_inputs_json={},
                analysis_depth="standard",
                owner_user_id=operator_record.id,
                visibility="private",
            )
        )
        db.add(
            ReportModel(
                id=base.report_id,
                analysis_request_id="analysis_phase21b_provenance",
                title="Synthetic report",
                risk_rating=base.risk_rating,
                summary=base.executive_summary,
                report_markdown="synthetic",
                report_json=base.model_dump(mode="json"),
                owner_user_id=operator_record.id,
                visibility="private",
            )
        )
        db.flush()
        record = record_model_run_provenance(
            db,
            report_id=base.report_id,
            candidate=build_report_synthesis_candidate(result, base, context, scope_class="private"),
            owner_user_id=operator_record.id,
            organization_id=None,
            anonymous_session_id=None,
        )
        db.commit()
        assert record.route_version_id == route.id
        assert record.evaluation_run_id == evaluation.id


def test_route_identity_mismatch_and_private_policy_fail_closed(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-policy-admin@example.test", role="admin"))
        private_provider = SyntheticProvider()
        run = evaluate_report_synthesis_candidate(db, provider=private_provider, actor=operator)
        promote_evaluation_route(db, evaluation_run_id=run.id, actor=operator)
        mismatch = resolve_report_synthesis_route(db, content_scope="public", configured_provider=PublicOnlyProvider())
        assert mismatch.provider is None
        assert mismatch.fallback_reason == "configured_provider_mismatch"

        route_id = db.scalar(select(ModelRouteAssignmentModel.active_route_version_id))
        assert route_id is not None
        route = db.get(ModelRouteVersionModel, route_id)
        assert route is not None
        candidate = db.get(ModelRegistryModel, route.model_registry_id)
        assert candidate is not None
        candidate.privacy_classification = "public_only"
        db.commit()
        denied = resolve_report_synthesis_route(db, content_scope="private", configured_provider=PublicOnlyProvider())
        assert denied.provider is None
        assert denied.validation_result == "policy_denied"
        assert denied.fallback_reason == "private_provider_not_approved"


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("development", "development"),
        ("dev", "development"),
        ("test", "test"),
        ("testing", "test"),
        ("staging", "staging"),
        ("production", "production"),
        ("prod", "production"),
        ("portfolio_demo", "portfolio_demo"),
        ("exercise", "exercise"),
    ],
)
def test_server_environment_accepts_only_documented_server_aliases(configured: str, expected: str) -> None:
    assert server_environment(Settings(app_env=configured, public_demo_mode=False)) == expected
    assert server_environment(Settings(app_env="unsupported-environment", public_demo_mode=False)) is None
    assert server_environment(Settings(app_env="unsupported-environment", public_demo_mode=True)) == "portfolio_demo"


def test_unknown_environment_never_uses_development_route_or_browser_data(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-environment-admin@example.test", role="admin"))
        provider = SyntheticProvider()
        run = evaluate_report_synthesis_candidate(db, provider=provider, actor=operator)
        promote_evaluation_route(db, evaluation_run_id=run.id, actor=operator)
        resolution = resolve_report_synthesis_route(
            db,
            content_scope="public",
            configured_provider=provider,
            settings=Settings(app_env="typoed-environment", llm_synthesis_enabled=True),
        )
        assert resolution.provider is None
        assert resolution.fallback_reason == "unsupported_environment"
        with pytest.raises(ValueError, match="environment"):
            AnalysisRequest.model_validate(
                {
                    "strategy_description": "A bounded analysis request cannot choose model environment.",
                    "protocols": ["aave"],
                    "manual_inputs": {},
                    "environment": "production",
                }
            )


def test_promotion_requires_current_policy_and_authoritative_dataset(routing_session) -> None:
    with routing_session() as db:
        operator = user_context(create_user(db, "phase21b-promotion-evidence@example.test", role="admin"))
        current_run = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(), actor=operator)
        assert promote_evaluation_route(db, evaluation_run_id=current_run.id, actor=operator).evaluation_run_id == current_run.id

        stale_policy = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="stale-policy"), actor=operator)
        db.execute(
            ModelEvaluationRunModel.__table__.update()
            .where(ModelEvaluationRunModel.id == stale_policy.id)
            .values(policy_version="report_synthesis.promotion.old")
        )
        db.expire_all()
        with pytest.raises(ModelEvaluationError, match="current promotion policy"):
            promote_evaluation_route(db, evaluation_run_id=stale_policy.id, actor=operator)
        db.rollback()

        stale_checksum = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="stale-checksum"), actor=operator)
        db.execute(
            ModelEvaluationRunModel.__table__.update()
            .where(ModelEvaluationRunModel.id == stale_checksum.id)
            .values(policy_checksum="0" * 64)
        )
        db.expire_all()
        with pytest.raises(ModelEvaluationError, match="current promotion policy"):
            promote_evaluation_route(db, evaluation_run_id=stale_checksum.id, actor=operator)
        db.rollback()

        stale_dataset = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="stale-dataset"), actor=operator)
        db.execute(
            ModelEvaluationDatasetModel.__table__.update()
            .where(ModelEvaluationDatasetModel.id == stale_dataset.dataset_id)
            .values(dataset_checksum="0" * 64)
        )
        db.expire_all()
        with pytest.raises(ModelEvaluationError, match="current authoritative dataset"):
            promote_evaluation_route(db, evaluation_run_id=stale_dataset.id, actor=operator)
        db.rollback()

        incomplete = evaluate_report_synthesis_candidate(db, provider=SyntheticProvider(model="incomplete-run"), actor=operator)
        db.execute(
            ModelEvaluationRunModel.__table__.update()
            .where(ModelEvaluationRunModel.id == incomplete.id)
            .values(status="running", promotion_eligible=False)
        )
        db.expire_all()
        with pytest.raises(ModelEvaluationError, match="Passing completed"):
            promote_evaluation_route(db, evaluation_run_id=incomplete.id, actor=operator)


def _runtime_inputs():
    from app.llm.evaluation import _evaluation_context, _evaluation_market_data, _evaluation_report, _evaluation_risk

    case = report_synthesis_public_dataset().cases[0]
    return _evaluation_report(case), _evaluation_context(case), _evaluation_market_data(), _evaluation_risk()
