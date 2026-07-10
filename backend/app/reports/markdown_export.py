from app.reports.renderer import validate_report_structure
from app.schemas.reports import ReportResponse


def render_markdown_report(report: ReportResponse) -> str:
    validate_report_structure(report)
    sections = "\n\n".join(
        f"## {section.title}\n\n{section.content}" for section in report.sections
    )
    return (
        f"# Strategy Risk Report\n\n"
        f"Report ID: `{report.report_id}`\n\n"
        f"Risk rating: **{report.risk_rating}**\n\n"
        f"## Executive Summary\n\n{report.executive_summary}\n\n"
        f"{sections}\n"
    )
