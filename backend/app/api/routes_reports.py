from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_actor
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.schemas.reports import MarkdownExportResponse, ReportResponse
from app.services.report_service import get_report, get_report_markdown

router = APIRouter(tags=["reports"])


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
