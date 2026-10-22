import type { ResearchRunMetadata } from "@/lib/types";
import { safeCitationHref } from "@/lib/citation-url";

type ResearchRunEvidencePanelProps = {
  research: ResearchRunMetadata;
};

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "timestamp unavailable" : date.toLocaleString();
}

export function ResearchRunEvidencePanel({ research }: ResearchRunEvidencePanelProps) {
  return (
    <section className="panel stack" aria-labelledby="research-run-evidence-heading">
      <h2 id="research-run-evidence-heading">Research run provenance</h2>
      <p><strong>Question:</strong> {research.question}</p>
      <p>
        {research.status === "completed_with_gaps" ? "Completed with evidence gaps" : "Completed"}.{" "}
        {research.pass_count} of {research.limits.max_passes} passes; {research.tool_invocation_count} of{" "}
        {research.limits.max_tool_invocations} tool invocations; {research.source_document_count} of{" "}
        {research.limits.max_documents} source documents; {research.elapsed_ms} ms.
      </p>
      <p>
        {research.llm_used
          ? `Approved route used: ${research.model_provider ?? "provider unknown"} / ${research.model_key ?? "model unknown"}.`
          : `Deterministic synthesis used; provider call state: ${research.provider_call_state}${research.llm_fallback_reason ? ` · ${research.llm_fallback_reason}` : ""}.`}
      </p>
      <p className="muted-small">
        Provider calls observed: {research.model_call_count}; usage: {research.usage_status}; effective total used for the budget: {research.total_tokens ?? "unknown"} tokens; provider-reported total: {research.reported_total_tokens ?? "unknown"}; cost: {research.cost_microusd === null || research.cost_microusd === undefined ? "unknown" : `${research.cost_microusd} microUSD`}.
      </p>
      <div>
        <h3>Bounded tool trace</h3>
        <ul className="compact-list">
          {research.tools.map((tool, index) => (
            <li key={`${tool.tool}-${tool.pass_number}-${index}`}>
              Pass {tool.pass_number}: {tool.tool} — {tool.status}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3>Source observations and freshness</h3>
        <ul className="source-list">
          {research.sources.map((source) => (
            <li key={`${source.source_id}-${source.status}`}>
              <strong>{source.title}</strong>
              <span>{source.source_type}{source.protocol ? ` · ${source.protocol}` : ""} · {source.status}</span>
              {source.source_version_id ? <span>Source version: {source.source_version_id}</span> : <span>Source version: unavailable</span>}
              {source.source_version_checksum ? <span>Version checksum: {source.source_version_checksum}</span> : null}
              <span>Observed: {dateLabel(source.observed_at)}</span>
              {source.source_timestamp ? <span>Source timestamp: {dateLabel(source.source_timestamp)}</span> : null}
              <span>{source.freshness_note}</span>
              {safeCitationHref(source.url) ? <a className="text-link" href={safeCitationHref(source.url) ?? undefined} rel="noreferrer" target="_blank">Open source</a> : null}
            </li>
          ))}
        </ul>
      </div>
      {research.evidence_gaps.length ? (
        <div>
          <h3>Unresolved evidence</h3>
          <ul className="compact-list">
            {research.evidence_gaps.map((gap, index) => <li key={`${gap}-${index}`}>{gap}</li>)}
          </ul>
        </div>
      ) : null}
      <p className="muted-small">Run {research.run_id} · Started {dateLabel(research.started_at)} · Completed {dateLabel(research.completed_at)}</p>
    </section>
  );
}
