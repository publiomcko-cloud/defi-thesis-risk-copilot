from sqlalchemy.orm import Session

from app.models.report import ReportModel
from app.schemas.reports import ReportResponse


def save_report(
    report: ReportResponse,
    analysis_request_id: str,
    report_markdown: str,
    db: Session,
) -> ReportResponse:
    db.add(
        ReportModel(
            id=report.report_id,
            analysis_request_id=analysis_request_id,
            title="Strategy Risk Report",
            risk_rating=report.risk_rating,
            summary=report.executive_summary,
            report_markdown=report_markdown,
            report_json=report.model_dump(mode="json"),
        )
    )
    return report


def get_report(report_id: str, db: Session) -> ReportResponse | None:
    record = db.get(ReportModel, report_id)
    if record is None:
        return None
    return ReportResponse.model_validate(record.report_json)


def get_report_markdown(report_id: str, db: Session) -> str | None:
    record = db.get(ReportModel, report_id)
    if record is None:
        return None
    return record.report_markdown
