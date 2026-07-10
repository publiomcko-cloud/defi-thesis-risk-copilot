from app.reports.templates import REQUIRED_REPORT_SECTIONS
from app.schemas.reports import ReportResponse, ReportSection


def validate_report_structure(report: ReportResponse) -> None:
    titles = [section.title for section in report.sections]
    missing = [title for title in REQUIRED_REPORT_SECTIONS if title not in titles]
    if missing:
        raise ValueError(f"Report is missing required sections: {', '.join(missing)}")


def make_section(title: str, content: str) -> ReportSection:
    return ReportSection(title=title, content=content)
