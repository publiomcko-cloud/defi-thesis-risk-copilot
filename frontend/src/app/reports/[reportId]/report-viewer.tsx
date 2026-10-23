"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DataSummaryTable } from "@/components/DataSummaryTable";
import { DisclaimerBox } from "@/components/DisclaimerBox";
import { MarkdownExportButton } from "@/components/MarkdownExportButton";
import { MonitoringChecklist } from "@/components/MonitoringChecklist";
import { ReportSection } from "@/components/ReportSection";
import { RiskRatingCard } from "@/components/RiskRatingCard";
import { ReportFeedbackForm } from "@/components/ReportFeedbackForm";
import { ReportResearchPanel } from "@/components/ReportResearchPanel";
import { ResearchRunEvidencePanel } from "@/components/ResearchRunEvidencePanel";
import { SourcesPanel } from "@/components/SourcesPanel";
import { fetchReport } from "@/lib/api";
import { formatProtocolName } from "@/lib/formatting";
import type { ReportResponse } from "@/lib/types";
import { safeCitationHref } from "@/lib/citation-url";

type ReportViewerProps = {
  reportId: string;
};

const separatelyRenderedSections = new Set([
  "Monitoring Checklist",
  "Sources",
  "Disclaimer",
  "Risk Rating",
  "Question-Specific Answer"
]);

export function ReportViewer({ reportId }: ReportViewerProps) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadReport = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setReport(await fetchReport(reportId));
    } catch (caught) {
      setReport(null);
      setError(caught instanceof Error ? caught.message : "Report fetch failed.");
    } finally {
      setIsLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  const visibleSections = useMemo(
    () => report?.sections.filter((section) => !separatelyRenderedSections.has(section.title)) ?? [],
    [report]
  );

  if (isLoading) {
    return (
      <main className="page narrow-page">
        <section className="panel loading-panel" aria-live="polite">
          <div className="loading-indicator" aria-hidden="true" />
          <h1>Loading report</h1>
          <p>
            Fetching the persisted report. The free-tier backend may need a short cold start.
          </p>
        </section>
      </main>
    );
  }

  if (error || report === null) {
    return (
      <main className="page narrow-page">
        <section className="panel">
          <h1>Report temporarily unavailable</h1>
          <p>{error ?? "The report could not be loaded."}</p>
          <p>
            The hosted backend may be waking up. Check readiness, then retry without
            leaving this page.
          </p>
          <div className="action-row">
            <button className="primary-action" onClick={() => void loadReport()} type="button">
              Retry report
            </button>
            <a
              className="secondary-link"
              href="https://defi-thesis-risk-copilot.onrender.com/ready"
              rel="noreferrer"
              target="_blank"
            >
              Check backend readiness
            </a>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Persisted research report</p>
        <h1>Strategy Risk Report</h1>
        <p>{report.executive_summary}</p>
        <p className="tag-row">
          {report.protocols.map((protocol) => (
            <span className="tag" key={protocol}>
              {formatProtocolName(protocol)}
            </span>
          ))}
        </p>
        <p className="field-help">Report ID: {report.report_id}</p>
      </section>

      <section className="content-grid">
        <RiskRatingCard rating={report.risk_rating} />
        <DataSummaryTable assumptions={report.assumptions} missingData={report.missing_data} />
      </section>

      <section className="stack">
        {visibleSections.map((section) => (
          <ReportSection key={section.title} section={section} />
        ))}
      </section>

      {report.question_answer ? (
        <section className="panel stack" aria-labelledby="question-answer-heading">
          <h2 id="question-answer-heading">Answer to the research question</h2>
          <p><strong>Evidence status:</strong> {report.question_answer.status}</p>
          <p>{report.question_answer.answer}</p>
          {report.question_answer.citations.length ? (
            <ol className="compact-list">
              {report.question_answer.citations.map((citation, index) => (
                <li key={`${citation.source_id}-${index}`}>
                  <strong>[S{index + 1}] {citation.title}</strong>
                  <p>{citation.excerpt}</p>
                  {safeCitationHref(citation.url) ? <a className="text-link" href={safeCitationHref(citation.url) ?? undefined} rel="noreferrer" target="_blank">Open cited source</a> : null}
                </li>
              ))}
            </ol>
          ) : null}
          {report.question_answer.unsupported_aspects.length ? <p>Unsupported aspects: {report.question_answer.unsupported_aspects.join(", ")}</p> : null}
          {report.question_answer.potential_contradictions.length ? (
            <div><h3>Potential contradictions</h3><ul className="compact-list">{report.question_answer.potential_contradictions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></div>
          ) : <p>No potential contradiction was detected by the bounded lexical check; semantic conflicts may still be missed.</p>}
          <p className="muted-small">{report.question_answer.method}</p>
        </section>
      ) : null}

      {report.research ? <ResearchRunEvidencePanel research={report.research} /> : null}

      <section className="content-grid">
        <MonitoringChecklist />
        <SourcesPanel sources={report.sources} />
      </section>

      <MarkdownExportButton reportId={report.report_id} />
      <ReportResearchPanel reportId={report.report_id} />
      <ReportFeedbackForm reportId={report.report_id} />
      <DisclaimerBox text={report.disclaimer} />
    </main>
  );
}
