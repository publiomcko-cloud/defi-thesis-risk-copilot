"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Revision = {
  revision_number: number;
  status: string;
  change_reason?: string | null;
  created_at: string;
};

type Assumption = {
  id: string;
  revision_number: number;
  statement: string;
  state: string;
};

type Catalyst = {
  id: string;
  title: string;
  date_precision: string;
  expected_date?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  status: string;
  uncertainty?: string | null;
};

type ThesisResearchPanelProps = {
  thesisId: string;
};

export function ThesisResearchPanel({ thesisId }: ThesisResearchPanelProps) {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [assumptions, setAssumptions] = useState<Assumption[]>([]);
  const [catalysts, setCatalysts] = useState<Catalyst[]>([]);
  const [questions, setQuestions] = useState<string[]>([]);
  const [status, setStatus] = useState("draft");
  const [assumption, setAssumption] = useState("");
  const [catalystTitle, setCatalystTitle] = useState("");
  const [catalystDate, setCatalystDate] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const [history, assumptionResponse, catalystResponse, questionsResponse] = await Promise.all([
      fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/history`, { cache: "no-store" }),
      fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/assumptions`, { cache: "no-store" }),
      fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/catalysts`, { cache: "no-store" }),
      fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/monitoring-questions`, { cache: "no-store" })
    ]);
    if (history.ok) {
      const body = await history.json();
      const items = body.items as Revision[];
      setRevisions(items);
      setStatus(items.at(-1)?.status ?? "draft");
    }
    if (assumptionResponse.ok) setAssumptions((await assumptionResponse.json()).items as Assumption[]);
    if (catalystResponse.ok) setCatalysts((await catalystResponse.json()).items as Catalyst[]);
    if (questionsResponse.ok) setQuestions((await questionsResponse.json()).questions as string[]);
  }, [thesisId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function changeStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const expectedRevision = revisions.at(-1)?.revision_number;
    const response = await fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, expected_revision: expectedRevision })
    });
    setMessage(response.ok ? "Research status updated." : "The thesis changed before the status could be saved.");
    if (response.ok) await refresh();
  }

  async function addAssumption(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/assumptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ statement: assumption, state: "active", evidence_references: [] })
    });
    setMessage(response.ok ? "Assumption recorded." : "Unable to record the assumption.");
    if (response.ok) {
      setAssumption("");
      await refresh();
    }
  }

  async function addCatalyst(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = catalystDate
      ? { title: catalystTitle, date_precision: "exact", expected_date: catalystDate, evidence_references: [] }
      : { title: catalystTitle, date_precision: "unknown", evidence_references: [] };
    const response = await fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/catalysts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setMessage(response.ok ? "Catalyst recorded." : "Unable to record the catalyst.");
    if (response.ok) {
      setCatalystTitle("");
      setCatalystDate("");
      await refresh();
    }
  }

  return (
    <section aria-labelledby={`research-${thesisId}`} className="stack research-intelligence">
      <h3 id={`research-${thesisId}`}>Research intelligence</h3>
      <form className="action-row compact-actions" onSubmit={changeStatus}>
        <label>
          Thesis status
          <select onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="challenged">Challenged</option>
            <option value="invalidated">Invalidated</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <button className="secondary-action" type="submit">Update status</button>
      </form>
      <div>
        <h4>Revision timeline</h4>
        <ul className="compact-list">
          {revisions.map((item) => <li key={item.revision_number}>Revision {item.revision_number}: {item.status}{item.change_reason ? ` - ${item.change_reason}` : ""}</li>)}
        </ul>
      </div>
      <form className="action-row compact-actions" onSubmit={addAssumption}>
        <label>
          Assumption
          <input onChange={(event) => setAssumption(event.target.value)} required value={assumption} />
        </label>
        <button className="secondary-action" type="submit">Record assumption</button>
      </form>
      <div>
        <h4>Assumption changes</h4>
        <ul className="compact-list">
          {assumptions.map((item) => <li key={`${item.id}-${item.revision_number}`}>{item.state}: {item.statement}</li>)}
        </ul>
      </div>
      <form className="action-row compact-actions" onSubmit={addCatalyst}>
        <label>
          Catalyst
          <input onChange={(event) => setCatalystTitle(event.target.value)} required value={catalystTitle} />
        </label>
        <label>
          Expected date
          <input onChange={(event) => setCatalystDate(event.target.value)} type="date" value={catalystDate} />
        </label>
        <button className="secondary-action" type="submit">Record catalyst</button>
      </form>
      <div>
        <h4>Catalysts</h4>
        <ul className="compact-list">
          {catalysts.map((item) => <li key={item.id}>{item.status}: {item.title} ({item.expected_date ?? item.window_start ?? "date unknown"})</li>)}
        </ul>
      </div>
      <div>
        <h4>Monitoring questions</h4>
        <ul className="compact-list">{questions.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
