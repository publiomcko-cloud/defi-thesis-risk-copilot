"use client";

import { useEffect, useState } from "react";

import { DataSummaryTable } from "@/components/DataSummaryTable";
import { DisclaimerBox } from "@/components/DisclaimerBox";
import { MonitoringChecklist } from "@/components/MonitoringChecklist";
import { MarkdownExportButton } from "@/components/MarkdownExportButton";
import { ReportSection } from "@/components/ReportSection";
import { RiskRatingCard } from "@/components/RiskRatingCard";
import { SourcesPanel } from "@/components/SourcesPanel";
import { fetchReport } from "@/lib/api";
import { formatProtocolName } from "@/lib/formatting";
import type { ReportResponse } from "@/lib/types";

type ReportViewerProps = {
  reportId: string;
};

export function ReportViewer({ reportId }: ReportViewerProps) {
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    fetchReport(reportId)
      .then((payload) => {
        if (isMounted) {
          setReport(payload);
        }
      })
      .catch((caught) => {
        if (isMounted) {
          setError(
            caught instanceof Error ? caught.message : "Report fetch failed."
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [reportId]);

  if (isLoading) {
    return (
      <main className="page narrow-page">
        <section className="panel">
          <h1>Loading report</h1>
          <p>Fetching persisted report data from the backend API.</p>
        </section>
      </main>
    );
  }

  if (error || report === null) {
    return (
      <main className="page narrow-page">
        <section className="panel">
          <h1>Report unavailable</h1>
          <p>{error ?? "The report could not be loaded."}</p>
          <p>
            Reports are stored by the backend persistence layer. If this report
            is unavailable, confirm the backend is running and the local database
            has been migrated.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Report {report.report_id}</p>
        <h1>Strategy Risk Report</h1>
        <p>{report.executive_summary}</p>
        <p className="tag-row">
          {report.protocols.map((protocol) => (
            <span className="tag" key={protocol}>
              {formatProtocolName(protocol)}
            </span>
          ))}
        </p>
      </section>

      <section className="content-grid">
        <RiskRatingCard rating={report.risk_rating} />
        <DataSummaryTable
          assumptions={report.assumptions}
          missingData={report.missing_data}
        />
      </section>

      <section className="stack">
        {report.sections.map((section) => (
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
