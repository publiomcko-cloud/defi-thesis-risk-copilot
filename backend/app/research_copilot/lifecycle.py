"""Scrub F1 private research data with its thesis/account lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.llm.governance import remove_model_runs_for_expired_reports
from app.llm.feedback import dispose_model_feedback_for_reports
from app.research_copilot.execution import try_acquire_execution_lock


class ActiveResearchRunError(RuntimeError):
    pass


def dispose_research_runs_for_thesis(db: Session, thesis_id: str, now: datetime | None = None) -> None:
    runs = db.execute(
        select(AnalysisRequestModel)
        .where(AnalysisRequestModel.thesis_id == thesis_id)
        .where(AnalysisRequestModel.research_run_key.is_not(None))
        .where(AnalysisRequestModel.deleted_at.is_(None))
        .with_for_update()
    ).scalars().all()
    _dispose_runs(db, runs, now or datetime.now(UTC))


def dispose_research_runs_for_account(db: Session, owner_user_id: str, now: datetime | None = None) -> None:
    runs = db.execute(
        select(AnalysisRequestModel)
        .where(AnalysisRequestModel.owner_user_id == owner_user_id)
        .where(AnalysisRequestModel.research_run_key.is_not(None))
        .where(AnalysisRequestModel.deleted_at.is_(None))
        .with_for_update()
    ).scalars().all()
    _dispose_runs(db, runs, now or datetime.now(UTC))


def _dispose_runs(db: Session, runs: list[AnalysisRequestModel], now: datetime) -> None:
    for run in runs:
        previous_status = run.research_status
        if run.research_status == "running":
            if db.get_bind().dialect.name != "postgresql" or not try_acquire_execution_lock(db, run.id):
                raise ActiveResearchRunError("A research run may still be executing; disposal is deferred.")
        reports = db.execute(
            select(ReportModel).where(ReportModel.analysis_request_id == run.id).with_for_update()
        ).scalars().all()
        dispose_model_feedback_for_reports(db, [report.id for report in reports])
        remove_model_runs_for_expired_reports(db, [report.id for report in reports])
        for report in reports:
            report.deleted_at = now
            report.title = "Disposed research report"
            report.summary = ""
            report.report_markdown = ""
            report.report_json = {
                "report_id": report.id,
                "status": "deleted",
                "disposition": "private_research_data_disposed",
            }
        run.deleted_at = now
        run.research_completed_at = now
        run.research_question = None
        run.strategy_description = "[disposed]"
        run.protocols = []
        run.market_url = None
        run.manual_inputs_json = {}
        run.research_metadata_json = {
            "disposition": "private_research_data_disposed",
            "disposed_at": now.isoformat(),
            "previous_status": previous_status,
        }
