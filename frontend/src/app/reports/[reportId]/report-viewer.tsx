"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DataSummaryTable } from "@/components/DataSummaryTable";
import { DisclaimerBox } from "@/components/DisclaimerBox";
import { MarkdownExportButton } from "@/components/MarkdownExportButton";
import { MonitoringChecklist } from "@/components/MonitoringChecklist";
import { ReportSection } from "@/components/ReportSection";
import { RiskRatingCard } from "@/components/RiskRatingCard";
import { SourcesPanel } from "@/components/SourcesPanel";
import { fetchReport } from "@/lib/api";
import { formatProtocolName } from "@/lib/formatting";
import type { ReportResponse } from "@/lib/types";

type ReportViewerProps = {
  reportId: string;
};

const separatelyRenderedSections = new Set([
  "Monitoring Checklist",
  "Sources",
  "Disclaimer",
  "Risk Rating"
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

      <section className="content-grid">
        <MonitoringChecklist />
        <SourcesPanel sources={report.sources} />
      </section>

      <MarkdownExportButton reportId={report.report_id} />
      <DisclaimerBox text={report.disclaimer} />
    </main>
  );
}
