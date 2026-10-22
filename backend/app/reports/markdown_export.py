from app.reports.renderer import validate_report_structure
from app.schemas.reports import ReportResponse


def render_markdown_report(report: ReportResponse) -> str:
    validate_report_structure(report)
    research_provenance = _render_research_provenance(report)
    sections = "\n\n".join(
        f"## {section.title}\n\n{section.content}" for section in report.sections
    )
    return (
        f"# Strategy Risk Report\n\n"
        f"Report ID: `{report.report_id}`\n\n"
        f"Risk rating: **{report.risk_rating}**\n\n"
        f"## Executive Summary\n\n{report.executive_summary}\n\n"
        f"{research_provenance}"
        f"{sections}\n"
    )


def _render_research_provenance(report: ReportResponse) -> str:
    research = report.research
    if research is None:
        return ""
    sources = "\n".join(
        f"- {source.title} ({source.status}; version {source.source_version_id or 'not supplied'}; "
        f"version checksum {source.source_version_checksum or 'not supplied'}; observed {source.observed_at.isoformat()}): "
        f"{source.freshness_note}{f' — {source.url}' if source.url else ''}"
        for source in research.sources
    ) or "- No source observations recorded."
    gaps = "\n".join(f"- {gap}" for gap in research.evidence_gaps) or "- No evidence gaps reported."
    tools = "\n".join(
        f"- Pass {tool.pass_number}: {tool.tool} ({tool.status})"
        for tool in research.tools
    ) or "- No tool calls recorded."
    model_usage = (
        f"Approved model route used: {research.model_provider or 'unknown'} / {research.model_key or 'unknown'}."
        if research.llm_used
        else f"No LLM output used; deterministic fallback ({research.llm_outcome})."
    )
    return (
        "## Bounded Research Provenance\n\n"
        f"Run: `{research.run_id}` · Thesis: `{research.thesis_id}` · Status: **{research.status}**\n\n"
        f"Question: {research.question}\n\n"
        f"Passes: {research.pass_count}/{research.limits.max_passes}; "
        f"tools: {research.tool_invocation_count}/{research.limits.max_tool_invocations}; "
        f"documents: {research.source_document_count}/{research.limits.max_documents}; "
        f"wall time: {research.elapsed_ms} ms.\n\n"
        f"{model_usage}\n\n"
        f"### Tool Trace\n\n{tools}\n\n"
        f"### Source Observations\n\n{sources}\n\n"
        f"### Evidence Gaps\n\n{gaps}\n\n"
    )
