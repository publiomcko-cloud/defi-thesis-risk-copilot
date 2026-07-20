from datetime import datetime

from sqlalchemy.orm import Session

from app.auth.policies import can_read_resource
from app.auth.schemas import UserContext
from app.models.report import ReportModel
from app.schemas.reports import ReportResponse


def save_report(
    report: ReportResponse,
    analysis_request_id: str,
    report_markdown: str,
    db: Session,
    owner_user_id: str | None = None,
    organization_id: str | None = None,
    visibility: str = "private",
    anonymous_session_id: str | None = None,
    expires_at: datetime | None = None,
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
            owner_user_id=owner_user_id,
            organization_id=organization_id,
            visibility=visibility,
            anonymous_session_id=anonymous_session_id,
            expires_at=expires_at,
        )
    )
    return report


def get_report(
    report_id: str,
    db: Session,
    actor: UserContext | None = None,
) -> ReportResponse | None:
    record = db.get(ReportModel, report_id)
    if record is None:
        return None
    if not can_read_resource(actor, record, db):
        return None
    return ReportResponse.model_validate(record.report_json)


def get_report_markdown(
    report_id: str,
    db: Session,
    actor: UserContext | None = None,
) -> str | None:
    record = db.get(ReportModel, report_id)
    if record is None:
        return None
    if not can_read_resource(actor, record, db):
        return None
    return record.report_markdown
