"use client";

import { FormEvent, useEffect, useState } from "react";

type ReportResearchPanelProps = {
  reportId: string;
};

export function ReportResearchPanel({ reportId }: ReportResearchPanelProps) {
  const [comparisonId, setComparisonId] = useState("");
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null);
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
    setComparison(body.changes as Record<string, unknown>);
    setMessage("Deterministic comparison ready.");
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
      {comparison ? <pre className="code-block">{JSON.stringify(comparison, null, 2)}</pre> : null}
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
