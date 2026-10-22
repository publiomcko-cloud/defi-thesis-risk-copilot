from __future__ import annotations

import multiprocessing
import os
import queue
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, event, select, text
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserContext
from app.db.session import create_database_engine
from app.llm.provenance import build_report_synthesis_candidate
from app.llm.synthesis import SynthesisResult
from app.models.analysis_request import AnalysisRequestModel
from app.models.model_governance import ModelRunProvenanceModel
from app.models.report import ReportModel
from app.models.saved_thesis import SavedThesisModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.reports.templates import REQUIRED_REPORT_SECTIONS
from app.research_copilot.execution import _owner_lock_id
from app.research_copilot.service import get_thesis_research_run, start_thesis_research
from app.schemas.market_data import MarketDataResponse
from app.schemas.reports import QuestionAnswer, ReportResponse, ReportSection
from app.schemas.research import ResearchQuestionRequest


pytestmark = pytest.mark.postgres_integration


def _actor(owner_id: str) -> UserContext:
    return UserContext(
        id=owner_id,
        email=f"{owner_id}@example.test",
        role="common",
        plan="free",
        is_active=True,
        auth_enabled=True,
    )


def _new_case(Session) -> tuple[str, str, str]:
    suffix = uuid4().hex
    owner_id = f"owner_{suffix}"
    thesis_id = f"thesis_{suffix}"
    key = f"phase22-f1c2-{suffix}"
    now = datetime.now(UTC)
    with Session() as db:
        db.add(
            UserModel(
                id=owner_id,
                email=f"{owner_id}@example.test",
                role="common",
                auth_provider="legacy_local",
                account_status="active",
                plan="free",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
        db.add(
            SavedThesisModel(
                id=thesis_id,
                owner_user_id=owner_id,
                organization_id=None,
                title="F1-C2 isolated ownership test",
                strategy_text="Review a Pendle position for maturity and liquidity risk.",
                protocols=["pendle"],
                assumptions_json={},
                visibility="private",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    return owner_id, thesis_id, key


def _cleanup_owner(Session, owner_id: str) -> None:
    with Session() as db:
        report_ids = select(ReportModel.id).where(ReportModel.owner_user_id == owner_id)
        db.execute(
            delete(ModelRunProvenanceModel).where(ModelRunProvenanceModel.report_id.in_(report_ids))
        )
        db.execute(delete(ReportModel).where(ReportModel.owner_user_id == owner_id))
        db.execute(delete(AnalysisRequestModel).where(AnalysisRequestModel.owner_user_id == owner_id))
        db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == owner_id))
        db.execute(delete(SavedThesisModel).where(SavedThesisModel.owner_user_id == owner_id))
        db.execute(delete(UserModel).where(UserModel.id == owner_id))
        db.commit()


def _synthetic_workflow(report_id: str, request, *, on_start=None, finish_event=None):
    if on_start is not None:
        on_start()
    if finish_event is not None and not finish_event.wait(20):
        raise TimeoutError("test workflow barrier was not released")
    report = ReportResponse(
        report_id=report_id,
        status="completed",
        risk_rating="Moderate",
        executive_summary="Synthetic deterministic research report.",
        strategy_description=request.strategy_description,
        research_question="How can maturity and liquidity change this thesis?",
        question_answer=QuestionAnswer(
            status="insufficient",
            answer="No answer is inferred by this synthetic concurrency fixture.",
            citations=[],
            unsupported_aspects=[],
            potential_contradictions=[],
            method="synthetic concurrency test",
        ),
        protocols=["pendle"],
        assumptions=[],
        missing_data=["Synthetic workflow fixture."],
        sections=[
            ReportSection(title=title, content="Synthetic deterministic output.")
            for title in REQUIRED_REPORT_SECTIONS
        ],
        sources=[],
    )
    model_result = SynthesisResult(
        report=report,
        used_llm=False,
        reason="disabled",
        outcome="disabled",
        validation_result="not_run",
    )
    return type(
        "SyntheticWorkflow",
        (),
        {
            "report": report,
            "missing_data": ["Synthetic workflow fixture."],
            "retrieved_context": [],
            "market_data": MarketDataResponse(
                status="partial",
                source="synthetic",
                data={},
                missing_fields=[],
                assumptions=[],
            ),
            "model_run": build_report_synthesis_candidate(model_result, report, [], scope_class="private"),
            "model_quality": None,
            "pass_count": 1,
            "model_call_count": 0,
            "tool_invocation_count": 1,
            "tool_trace": [],
            "provider_call_state": "not_attempted",
            "usage_status": "not_applicable",
        },
    )()


def _reader_process(database_url: str, owner_id: str, thesis_id: str, run_id: str, result_queue) -> None:
    engine = create_database_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with Session() as db:
            summary = get_thesis_research_run(db, _actor(owner_id), thesis_id, run_id)
            result_queue.put(("ok", summary.status))
    except HTTPException as exc:
        result_queue.put(("http", exc.status_code))
    except BaseException as exc:
        result_queue.put(("error", repr(exc)))
    finally:
        engine.dispose()


def _delete_thesis_process(database_url: str, owner_id: str, thesis_id: str, result_queue) -> None:
    from app.theses.service import delete_thesis

    engine = create_database_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with Session() as db:
            delete_thesis(db, _actor(owner_id), thesis_id)
        result_queue.put(("deleted", 200))
    except HTTPException as exc:
        result_queue.put(("http", exc.status_code))
    except BaseException as exc:
        result_queue.put(("error", repr(exc)))
    finally:
        engine.dispose()


def _same_key_process(database_url: str, owner_id: str, thesis_id: str, key: str, result_queue) -> None:
    import app.research_copilot.service as research_service

    engine = create_database_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    research_service.run_analysis_workflow = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("a concurrent same-key request must not start duplicate research")
    )
    try:
        with Session() as db:
            summary = start_thesis_research(
                db,
                _actor(owner_id),
                thesis_id,
                ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                key,
            )
            result_queue.put(("ok", summary.status))
    except HTTPException as exc:
        result_queue.put(("http", exc.status_code))
    except BaseException as exc:
        result_queue.put(("error", repr(exc)))
    finally:
        engine.dispose()


def _crash_before_acquisition_process(database_url: str, owner_id: str, thesis_id: str, key: str, ready, continue_event) -> None:
    import app.research_copilot.service as research_service

    real_lock = research_service.hold_research_owner_lock

    @contextmanager
    def paused_lock(db, requested_owner_id):
        ready.set()
        continue_event.wait()
        with real_lock(db, requested_owner_id) as acquired:
            yield acquired

    research_service.hold_research_owner_lock = paused_lock
    engine = create_database_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        with Session() as db:
            start_thesis_research(
                db,
                _actor(owner_id),
                thesis_id,
                ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                key,
            )
    finally:
        engine.dispose()


def _crash_after_reservation_process(database_url: str, owner_id: str, thesis_id: str, key: str) -> None:
    import app.research_copilot.service as research_service
    from app.quotas.service import consume_quota as real_consume_quota

    engine = create_database_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def commit_reservation_then_exit(db, actor, action):
        result = real_consume_quota(db, actor, action)
        os._exit(73)

    research_service.consume_quota = commit_reservation_then_exit
    with Session() as db:
        start_thesis_research(
            db,
            _actor(owner_id),
            thesis_id,
            ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
            key,
        )


def _database_url(engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def _postgres_session_factory():
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("F1-C2 ownership barriers require the isolated PostgreSQL CI profile")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("F1-C2 ownership barriers require PostgreSQL")
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_owner_fence_closes_reservation_handoff_and_deletion_races(monkeypatch) -> None:
    engine, Session = _postgres_session_factory()
    owner_id, thesis_id, key = _new_case(Session)
    database_url = _database_url(engine)
    context = multiprocessing.get_context("spawn")
    shared_workflow_calls = context.Value("i", 0)
    reservation_committed = threading.Event()
    continue_after_reservation = threading.Event()
    workflow_started = threading.Event()
    continue_workflow = context.Event()
    thread_result: queue.Queue = queue.Queue()

    import app.research_copilot.service as research_service

    def fake_workflow(_request, report_id, *_args, **kwargs):
        with shared_workflow_calls.get_lock():
            shared_workflow_calls.value += 1
        return _synthetic_workflow(
            report_id,
            _request,
            on_start=workflow_started.set,
            finish_event=continue_workflow,
        )

    monkeypatch.setattr(research_service, "run_analysis_workflow", fake_workflow)
    monkeypatch.setattr(research_service, "emit_product_event_safely", lambda *_args, **_kwargs: None)

    def pause_after_reservation(session) -> None:
        if not session.info.pop("pause_after_reservation", False):
            return
        reservation_committed.set()
        if not continue_after_reservation.wait(15):
            raise TimeoutError("reservation barrier was not released")

    event.listen(Session.class_, "after_commit", pause_after_reservation)

    def start_thread() -> None:
        try:
            with Session() as db:
                db.info["pause_after_reservation"] = True
                result = start_thesis_research(
                    db,
                    _actor(owner_id),
                    thesis_id,
                    ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                    key,
                )
            thread_result.put(("ok", result))
        except BaseException as exc:
            thread_result.put(("error", exc))

    thread = threading.Thread(target=start_thread, daemon=True)
    try:
        thread.start()
        assert reservation_committed.wait(15), "run reservation was not committed at the barrier"
        with Session() as db:
            run = db.execute(
                select(AnalysisRequestModel).where(AnalysisRequestModel.owner_user_id == owner_id)
            ).scalars().one()
            assert run.research_status == "running"
            run_id = run.id

        # The row is visible, but the owner transaction was acquired first and
        # remains open across the reservation/quota commit.
        probe_results = context.Queue()
        reader = context.Process(target=_reader_process, args=(database_url, owner_id, thesis_id, run_id, probe_results))
        reader.start()
        reader_status = probe_results.get(timeout=15)
        reader.join(timeout=15)
        assert reader.exitcode == 0
        assert reader_status == ("ok", "running")

        delete_results = context.Queue()
        deletion = context.Process(target=_delete_thesis_process, args=(database_url, owner_id, thesis_id, delete_results))
        deletion.start()
        deletion_result = delete_results.get(timeout=15)
        deletion.join(timeout=15)
        assert deletion.exitcode == 0
        assert deletion_result == ("http", 409)

        same_key_results = context.Queue()
        duplicate = context.Process(
            target=_same_key_process,
            args=(database_url, owner_id, thesis_id, key, same_key_results),
        )
        duplicate.start()
        duplicate_result = same_key_results.get(timeout=15)
        duplicate.join(timeout=15)
        assert duplicate.exitcode == 0
        assert duplicate_result == ("http", 409)

        continue_after_reservation.set()
        assert workflow_started.wait(15), "workflow did not reach its active-execution barrier"
        active_delete_results = context.Queue()
        active_deletion = context.Process(
            target=_delete_thesis_process,
            args=(database_url, owner_id, thesis_id, active_delete_results),
        )
        active_deletion.start()
        active_delete_result = active_delete_results.get(timeout=15)
        active_deletion.join(timeout=15)
        assert active_deletion.exitcode == 0
        assert active_delete_result == ("http", 409)

        continue_workflow.set()
        thread.join(timeout=20)
        assert not thread.is_alive()
        status, result = thread_result.get_nowait()
        assert status == "ok", repr(result)
        assert result.status == "completed_with_gaps"
        assert shared_workflow_calls.value == 1

        with Session() as db:
            stored_run = db.get(AnalysisRequestModel, run_id)
            assert stored_run is not None and stored_run.research_status == "completed"
            reports = db.execute(
                select(ReportModel).where(ReportModel.analysis_request_id == run_id)
            ).scalars().all()
            assert len(reports) == 1
            report_id = reports[0].id

            replay = start_thesis_research(
                db,
                _actor(owner_id),
                thesis_id,
                ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                key,
            )
            assert replay.run_id == run_id
            assert shared_workflow_calls.value == 1

        # Completion wins while execution owns the fence; a later deletion is
        # serialized after it and scrubs rather than resurrecting the report.
        from app.theses.service import delete_thesis

        with Session() as db:
            delete_thesis(db, _actor(owner_id), thesis_id)
        with Session() as db:
            disposed = db.get(ReportModel, report_id)
            assert disposed is not None and disposed.deleted_at is not None
            assert disposed.report_json == {
                "report_id": report_id,
                "status": "deleted",
                "disposition": "private_research_data_disposed",
            }
            thesis = db.get(SavedThesisModel, thesis_id)
            assert thesis is not None and thesis.deleted_at is not None
            with pytest.raises(HTTPException) as denied:
                start_thesis_research(
                    db,
                    _actor(owner_id),
                    thesis_id,
                    ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                    f"{key}-after-delete",
                )
            assert denied.value.status_code == 404
            assert shared_workflow_calls.value == 1
    finally:
        continue_after_reservation.set()
        continue_workflow.set()
        thread.join(timeout=20)
        event.remove(Session.class_, "after_commit", pause_after_reservation)
        _cleanup_owner(Session, owner_id)
        engine.dispose()


def test_postgres_crash_boundaries_never_replay_or_dispose_live_work(monkeypatch) -> None:
    engine, Session = _postgres_session_factory()
    context = multiprocessing.get_context("spawn")
    database_url = _database_url(engine)
    owners: list[str] = []
    try:
        # A process killed before attempting ownership cannot leave a visible
        # reservation or consume quota.
        owner_before, thesis_before, key_before = _new_case(Session)
        owners.append(owner_before)
        ready = context.Event()
        never_release = context.Event()
        before = context.Process(
            target=_crash_before_acquisition_process,
            args=(database_url, owner_before, thesis_before, key_before, ready, never_release),
        )
        before.start()
        assert ready.wait(15), "child did not pause before ownership acquisition"
        before.terminate()
        before.join(timeout=15)
        assert before.exitcode is not None
        with Session() as db:
            assert db.execute(
                select(AnalysisRequestModel).where(AnalysisRequestModel.owner_user_id == owner_before)
            ).scalars().all() == []
            assert db.execute(
                select(UsageQuotaModel).where(UsageQuotaModel.subject_id == owner_before)
            ).scalars().all() == []

        # After ownership and the reservation commit, process death releases
        # the still-open owner transaction. Reconciliation may then mark the
        # outcome uncertain, but it never replays the provider work.
        owner_after, thesis_after, key_after = _new_case(Session)
        owners.append(owner_after)
        crashed = context.Process(
            target=_crash_after_reservation_process,
            args=(database_url, owner_after, thesis_after, key_after),
        )
        crashed.start()
        crashed.join(timeout=20)
        assert crashed.exitcode == 73

        # This blocking lock acquisition is a synchronization barrier: it
        # returns only after PostgreSQL released the crashed process's xact
        # advisory lock. The timeout fails closed if cleanup does not occur.
        owner_lock_id = _owner_lock_id(owner_after)
        with engine.connect() as connection:
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": owner_lock_id},
            )
            connection.rollback()

        with Session() as db:
            run = db.execute(
                select(AnalysisRequestModel).where(AnalysisRequestModel.owner_user_id == owner_after)
            ).scalars().one()
            assert run.research_status == "running"
            from app.research_copilot.service import _reconcile_run_state

            _reconcile_run_state(db, run)
            assert run.research_status == "interrupted"
            assert run.research_metadata_json["outcome_certainty"] == "uncertain"
            assert run.research_metadata_json["provider_call_state"] == "uncertain"
            assert db.execute(
                select(ReportModel).where(ReportModel.analysis_request_id == run.id)
            ).scalars().all() == []
            quota = db.execute(
                select(UsageQuotaModel).where(UsageQuotaModel.subject_id == owner_after)
            ).scalars().one()
            assert quota.used == 1

            import app.research_copilot.service as research_service

            monkeypatch.setattr(
                research_service,
                "run_analysis_workflow",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError("uncertain interrupted work must never be replayed")
                ),
            )
            replay = start_thesis_research(
                db,
                _actor(owner_after),
                thesis_after,
                ResearchQuestionRequest(question="How can maturity and liquidity change this thesis?"),
                key_after,
            )
            assert replay.run_id == run.id
            assert replay.status == "interrupted"
    finally:
        for owner_id in owners:
            _cleanup_owner(Session, owner_id)
        engine.dispose()
