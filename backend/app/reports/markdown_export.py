import re

from app.reports.renderer import validate_report_structure
from app.schemas.reports import ReportResponse


def render_markdown_report(report: ReportResponse) -> str:
    validate_report_structure(report)
    research_provenance = _render_research_provenance(report)
    sections = "\n\n".join(
        f"## {section.title}\n\n{_safe_section_content(report, section.title, section.content)}"
        for section in report.sections
    )
    return (
        f"# Strategy Risk Report\n\n"
        f"Report ID: `{report.report_id}`\n\n"
        f"Risk rating: **{report.risk_rating}**\n\n"
        f"## Executive Summary\n\n{report.executive_summary}\n\n"
        f"{research_provenance}"
        f"{sections}\n"
    )


def _safe_section_content(report: ReportResponse, title: str, content: str) -> str:
    if title == "Sources":
        return "\n".join(
            f"- {_escape_markdown(source.title)} "
            f"({_escape_markdown(source.source_type)}{f'; {_escape_markdown(source.protocol)}' if source.protocol else ''})"
            f"{f' — {_inline_code(source.url)}' if source.url else ''}"
            for source in report.sources
        ) or "No sources were recorded."
    if title in {"Research Question", "Strategy Description"}:
        return _escape_markdown(content)
    if title == "Question-Specific Answer" and report.question_answer is not None:
        answer = report.question_answer
        lines = [f"Evidence status: {answer.status}", _escape_markdown(answer.answer)]
        for index, citation in enumerate(answer.citations, start=1):
            safe_excerpt = _inline_code(citation.excerpt)
            safe_url = f" — `{_inline_code(citation.url)}`" if citation.url else ""
            lines.append(f"[S{index}] {_escape_markdown(citation.title)}: {safe_excerpt}{safe_url}")
        if answer.unsupported_aspects:
            lines.append("Unresolved question terms: " + ", ".join(map(_escape_markdown, answer.unsupported_aspects)))
        lines.extend(_escape_markdown(item) for item in answer.potential_contradictions)
        lines.append(_escape_markdown(answer.method))
        return "\n\n".join(lines)
    return content


def _render_research_provenance(report: ReportResponse) -> str:
    research = report.research
    if research is None:
        return ""
    sources = "\n".join(
        f"- {_escape_markdown(source.title)} ({source.status}; version {source.source_version_id or 'not supplied'}; "
        f"version checksum {source.source_version_checksum or 'not supplied'}; observed {source.observed_at.isoformat()}): "
        f"{_escape_markdown(source.freshness_note)}{f' — `{_inline_code(source.url)}`' if source.url else ''}"
        for source in research.sources
    ) or "- No source observations recorded."
    gaps = "\n".join(f"- {_escape_markdown(gap)}" for gap in research.evidence_gaps) or "- No evidence gaps reported."
    tools = "\n".join(
        f"- Pass {tool.pass_number}: {tool.tool} ({tool.status})"
        for tool in research.tools
    ) or "- No tool calls recorded."
    model_usage = (
        f"Approved model route used: {research.model_provider or 'unknown'} / {research.model_key or 'unknown'}."
        if research.llm_used
        else f"Deterministic output used; provider call state {research.provider_call_state}; usage {research.usage_status} ({research.llm_outcome})."
    )
    usage = (
        f"Observed usage: effective total {research.total_tokens} tokens; provider-reported total "
        f"{research.reported_total_tokens if research.reported_total_tokens is not None else 'unknown'}; "
        f"{research.cost_microusd if research.cost_microusd is not None else 'unknown'} microUSD."
        if research.total_tokens is not None or research.cost_microusd is not None
        else "Observed token/cost usage: unknown."
    )
    return (
        "## Bounded Research Provenance\n\n"
        f"Run: `{research.run_id}` · Thesis: `{research.thesis_id}` · Status: **{research.status}**\n\n"
        f"Question: {_escape_markdown(research.question)}\n\n"
        f"Passes: {research.pass_count}/{research.limits.max_passes}; "
        f"tools: {research.tool_invocation_count}/{research.limits.max_tool_invocations}; "
        f"documents: {research.source_document_count}/{research.limits.max_documents}; "
        f"wall time: {research.elapsed_ms} ms.\n\n"
        f"{model_usage}\n\n"
        f"{usage}\n\n"
        f"### Tool Trace\n\n{tools}\n\n"
        f"### Source Observations\n\n{sources}\n\n"
        f"### Evidence Gaps\n\n{gaps}\n\n"
    )


def _escape_markdown(value: str) -> str:
    return "".join(f"\\{char}" if char in "\\`*_{}[]<>()#+-.!|" else char for char in value)


def _inline_code(value: str) -> str:
    fence = "`" * (max((len(run) for run in re.findall(r"`+", value)), default=0) + 1)
    padding = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{padding}{value}{padding}{fence}"
