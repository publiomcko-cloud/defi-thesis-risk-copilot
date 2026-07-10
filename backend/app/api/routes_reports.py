from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reports import ReportResponse
from app.services.report_service import get_report

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}", response_model=ReportResponse)
def read_report(
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportResponse:
    report = get_report(report_id, db)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
