"use client";

import { FormEvent, useEffect, useState } from "react";

type ReportResearchPanelProps = {
  reportId: string;
};

type Change = {
  status?: string;
  unchanged?: string[];
  added?: string[];
  removed?: string[];
  changed?: string[];
  left_content_origin?: string;
  right_content_origin?: string;
};

type Comparison = Record<string, Change | Record<string, Change> | { computation_origin?: string; left_synthesis_outcome?: string; right_synthesis_outcome?: string }>;

function changeSummary(change: Change) {
  const sets = ["unchanged", "added", "removed", "changed"] as const;
  const labels = sets.flatMap((key) => change[key]?.length ? [`${key}: ${change[key].join(", ")}`] : []);
  return labels.join("; ") || change.status || "No comparable value";
}

function origins(change: Change) {
  if (!change.left_content_origin && !change.right_content_origin) return null;
  return <span>Origin: left {change.left_content_origin ?? "unknown"}, right {change.right_content_origin ?? "unknown"}</span>;
}

export function ReportResearchPanel({ reportId }: ReportResearchPanelProps) {
  const [comparisonId, setComparisonId] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [uncertainty, setUncertainty] = useState<string[]>([]);
  const [staleness, setStaleness] = useState<Array<{ citation_id?: string; status: string; detail: string }>>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void fetch(`/api/backend/api/reports/${encodeURIComponent(reportId)}/source-staleness`, { cache: "no-store" })
      .then(async (response) => response.ok ? response.json() : null)
      .then((body) => setStaleness(body?.items ?? []));
  }, [reportId]);

  async function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/backend/api/reports/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ left_report_id: reportId, right_report_id: comparisonId })
    });
    if (!response.ok) {
      setMessage("The selected report is unavailable or is outside this research scope.");
      return;
    }
    const body = await response.json();
    setComparison(body.changes as Comparison);
    setUncertainty(Array.isArray(body.uncertainty) ? body.uncertainty : []);
    setMessage("Comparison ready. Content origins are shown below.");
  }

  return (
    <section aria-labelledby="report-research-heading" className="stack research-intelligence">
      <h2 id="report-research-heading">Research comparison</h2>
      <form className="action-row compact-actions" onSubmit={compare}>
        <label>
          Authorized report ID
          <input onChange={(event) => setComparisonId(event.target.value)} required value={comparisonId} />
        </label>
        <button className="secondary-action" type="submit">Compare reports</button>
      </form>
      {comparison ? <div className="stack" aria-live="polite">
        <div>
          <h3>Field changes</h3>
          <ul className="compact-list">
            {(["strategy", "protocols", "risk_rating", "assumptions", "missing_data", "timestamps"] as const).map((key) => {
              const change = comparison[key] as Change | undefined;
              return change ? <li key={key}><strong>{key.replaceAll("_", " ")}:</strong> {changeSummary(change)} {origins(change)}</li> : null;
            })}
          </ul>
        </div>
        <div>
          <h3>Section origins</h3>
          <ul className="compact-list">
            {Object.entries(comparison.sections as Record<string, Change> ?? {}).map(([title, change]) => <li key={title}><strong>{title}:</strong> {changeSummary(change)} {origins(change)}</li>)}
          </ul>
        </div>
        <div>
          <h3>Source and citation changes</h3>
          <ul className="compact-list">
            {(["sources", "citation_lineage"] as const).map((key) => {
              const change = comparison[key] as Change | undefined;
              return change ? <li key={key}><strong>{key.replaceAll("_", " ")}:</strong> {changeSummary(change)}</li> : null;
            })}
          </ul>
        </div>
        <div>
          <h3>Comparison provenance</h3>
          <p>
            Computation: {(comparison.comparison_provenance as { computation_origin?: string } | undefined)?.computation_origin ?? "unknown"}.{" "}
            Left synthesis: {(comparison.comparison_provenance as { left_synthesis_outcome?: string } | undefined)?.left_synthesis_outcome ?? "unknown"};{" "}
            right synthesis: {(comparison.comparison_provenance as { right_synthesis_outcome?: string } | undefined)?.right_synthesis_outcome ?? "unknown"}.
          </p>
        </div>
        <div>
          <h3>Uncertainty</h3>
          <ul className="compact-list">
            {uncertainty.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div> : null}
      <div>
        <h3>Evidence state</h3>
        <ul className="compact-list">
          {staleness.map((item, index) => <li key={`${item.citation_id ?? "source"}-${index}`}>{item.status}: {item.detail}</li>)}
        </ul>
      </div>
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
