from app.schemas.reports import ReportResponse

_reports: dict[str, ReportResponse] = {}


def save_report(report: ReportResponse) -> ReportResponse:
    _reports[report.report_id] = report
    return report


def get_report(report_id: str) -> ReportResponse | None:
    return _reports.get(report_id)
