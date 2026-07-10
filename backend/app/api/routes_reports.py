from fastapi import APIRouter, HTTPException

from app.schemas.reports import ReportResponse
from app.services.report_service import get_report

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}", response_model=ReportResponse)
def read_report(report_id: str) -> ReportResponse:
    report = get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
