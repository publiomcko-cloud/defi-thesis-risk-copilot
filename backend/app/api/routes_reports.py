from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.schemas.reports import MarkdownExportResponse, ReportResponse
from app.research_intelligence.schemas import (
    ReportComparisonRequest,
    ReportComparisonResponse,
    SourceStalenessResponse,
)
from app.research_intelligence.service import compare_reports, report_staleness
from app.services.report_service import get_report, get_report_markdown

router = APIRouter(tags=["reports"])


@router.post("/reports/compare", response_model=ReportComparisonResponse)
def compare_report_route(
    request: ReportComparisonRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> ReportComparisonResponse:
    return compare_reports(db, actor, request)


@router.get("/reports/{report_id}", response_model=ReportResponse)
def read_report(
    report_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> ReportResponse:
    report = get_report(report_id, db, actor)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports/{report_id}/source-staleness", response_model=SourceStalenessResponse)
def get_report_source_staleness(
    report_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> SourceStalenessResponse:
    return report_staleness(db, actor, report_id)


@router.post("/reports/{report_id}/export", response_model=MarkdownExportResponse)
def export_report_markdown(
    report_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_actor),
) -> MarkdownExportResponse:
    markdown = get_report_markdown(report_id, db, actor)
    if markdown is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return MarkdownExportResponse(
        report_id=report_id,
        filename=f"{report_id}.md",
        markdown=markdown,
    )
