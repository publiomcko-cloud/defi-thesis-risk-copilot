"use client";

import { useState } from "react";

import { exportReportMarkdown } from "@/lib/api";

type MarkdownExportButtonProps = {
  reportId: string;
};

export function MarkdownExportButton({ reportId }: MarkdownExportButtonProps) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleExport() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await exportReportMarkdown(reportId);
      setMarkdown(response.markdown);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Markdown export failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="panel">
      <h2>Markdown Export</h2>
      <button className="primary-action" disabled={isLoading} onClick={handleExport} type="button">
        {isLoading ? "Exporting..." : "Generate Markdown"}
      </button>
      {error ? <p className="error">{error}</p> : null}
      {markdown ? (
        <textarea aria-label="Markdown export" readOnly rows={12} value={markdown} />
      ) : null}
    </section>
  );
}
