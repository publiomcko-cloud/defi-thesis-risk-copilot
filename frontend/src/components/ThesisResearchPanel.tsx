"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ReportResearchPanel } from "@/components/ReportResearchPanel";
import type { ResearchRunSummary } from "@/lib/types";

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

async function fetchPanelResource(path: string): Promise<Response | null> {
  try {
    return await fetch(path, { cache: "no-store" });
  } catch {
    return null;
  }
}

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
  const [question, setQuestion] = useState("");
  const [runs, setRuns] = useState<ResearchRunSummary[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [pendingRunKey, setPendingRunKey] = useState<string | null>(null);
  const [pendingRunQuestion, setPendingRunQuestion] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [history, assumptionResponse, catalystResponse, questionsResponse, runResponse] = await Promise.all([
      fetchPanelResource(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/history`),
      fetchPanelResource(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/assumptions`),
      fetchPanelResource(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/catalysts`),
      fetchPanelResource(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/monitoring-questions`),
      fetchPanelResource(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/research-runs`),
    ]);
    if (history?.ok) {
      const body = await history.json();
      const items = body.items as Revision[];
      setRevisions(items);
      setStatus(items.at(-1)?.status ?? "draft");
    }
    if (assumptionResponse?.ok) setAssumptions((await assumptionResponse.json()).items as Assumption[]);
    if (catalystResponse?.ok) setCatalysts((await catalystResponse.json()).items as Catalyst[]);
    if (questionsResponse?.ok) setQuestions((await questionsResponse.json()).questions as string[]);
    if (runResponse?.ok) setRuns((await runResponse.json()).items as ResearchRunSummary[]);
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
    const expectedThesisRevision = revisions.at(-1)?.revision_number;
    const response = await fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/assumptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ statement: assumption, state: "active", evidence_references: [], expected_thesis_revision: expectedThesisRevision })
    });
    setMessage(response.ok ? "Assumption recorded." : "Unable to record the assumption.");
    if (response.ok) {
      setAssumption("");
      await refresh();
    }
  }

  async function addCatalyst(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const expected_thesis_revision = revisions.at(-1)?.revision_number;
    const payload = catalystDate
      ? { title: catalystTitle, date_precision: "exact", expected_date: catalystDate, evidence_references: [], expected_thesis_revision }
      : { title: catalystTitle, date_precision: "unknown", evidence_references: [], expected_thesis_revision };
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

  async function startResearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    const idempotencyKey = pendingRunKey && pendingRunQuestion === normalizedQuestion
      ? pendingRunKey
      : crypto.randomUUID();
    setPendingRunKey(idempotencyKey);
    setPendingRunQuestion(normalizedQuestion);
    setIsRunning(true);
    setMessage("Research request is running synchronously within the server time and tool limits.");
    try {
      const response = await fetch(`/api/backend/api/theses/${encodeURIComponent(thesisId)}/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey
        },
        body: JSON.stringify({ question: normalizedQuestion })
      });
      const body = await response.json() as ResearchRunSummary & { detail?: string };
      if (!response.ok) {
        throw new Error(body.detail ?? `Research request failed with status ${response.status}.`);
      }
      let run = body;
      if (run.status === "running") {
        setMessage("The run is reserved and still processing. Checking its persisted status.");
        for (let attempt = 0; attempt < 25 && run.status === "running"; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1_000));
          const statusResponse = await fetch(
            `/api/backend/api/theses/${encodeURIComponent(thesisId)}/research-runs/${encodeURIComponent(run.run_id)}`,
            { cache: "no-store" }
          );
          if (!statusResponse.ok) break;
          run = await statusResponse.json() as ResearchRunSummary;
        }
      }
      if (run.status === "failed") {
        setMessage(`Research failed safely (${run.error_code ?? "unknown error"}). No report was saved.`);
        setPendingRunKey(null);
        setPendingRunQuestion(null);
      } else if (run.status === "running") {
        setMessage("The run is still processing. Refresh the thesis workspace to check its saved status.");
      } else {
        setQuestion("");
        setPendingRunKey(null);
        setPendingRunQuestion(null);
        setMessage(run.metadata?.llm_used
          ? "Research report saved. The approved model route was used and recorded."
          : "Research report saved with deterministic synthesis; no approved model route was used.");
      }
      await refresh();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Research request could not be completed.");
    } finally {
      setIsRunning(false);
    }
  }

  const latestReport = runs.find((run) => run.status === "completed" && run.report_id)?.report_id;

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
      <form className="form-panel" onSubmit={startResearch}>
        <h4>Bounded synchronous research</h4>
        <p>Research runs inline with a two-pass maximum. No background worker is used.</p>
        <label>
          Research question
          <textarea maxLength={2000} minLength={10} onChange={(event) => setQuestion(event.target.value)} required rows={3} value={question} />
        </label>
        <button className="primary-action" disabled={isRunning || question.trim().length < 10} type="submit">
          {isRunning ? "Research running…" : "Start research"}
        </button>
      </form>
      <div>
        <h4>Saved research runs</h4>
        {runs.length ? (
          <ul className="compact-list">
            {runs.map((run) => (
              <li key={run.run_id}>
                {run.status === "completed"
                  ? (run.metadata?.status === "completed_with_gaps" ? "Completed with evidence gaps" : "Completed")
                  : run.status}
                : {run.question} · {new Date(run.started_at).toLocaleString()}
                {run.metadata ? ` · ${run.metadata.llm_used ? "LLM used" : "deterministic fallback"}` : ""}
                {run.report_id ? <> · <a className="text-link" href={`/reports/${encodeURIComponent(run.report_id)}`}>Open report</a></> : null}
                {run.error_code ? ` · ${run.error_code}` : ""}
              </li>
            ))}
          </ul>
        ) : <p>No research runs saved for this thesis.</p>}
      </div>
      {latestReport ? <ReportResearchPanel reportId={latestReport} /> : null}
      {message ? <p className={message.includes("failed") || message.includes("could not") ? "error" : "form-success"} aria-live="polite">{message}</p> : null}
    </section>
  );
}
