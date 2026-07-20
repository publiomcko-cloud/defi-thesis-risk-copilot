"use client";

import { useState } from "react";

import { exportReportMarkdown } from "@/lib/api";

type MarkdownExportButtonProps = {
  reportId: string;
};

export function MarkdownExportButton({ reportId }: MarkdownExportButtonProps) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [filename, setFilename] = useState(`${reportId}.md`);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleExport() {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await exportReportMarkdown(reportId);
      setMarkdown(response.markdown);
      setFilename(response.filename);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Markdown export failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCopy() {
    if (!markdown) {
      return;
    }
    await navigator.clipboard.writeText(markdown);
    setMessage("Markdown copied to clipboard.");
  }

  function handleDownload() {
    if (!markdown) {
      return;
    }
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    setMessage("Markdown download started.");
  }

  return (
    <section className="panel">
      <h2>Markdown Export</h2>
      <p>Generate a portable research artifact for review, versioning, or documentation.</p>
      <div className="action-row compact-actions">
        <button className="primary-action" disabled={isLoading} onClick={handleExport} type="button">
          {isLoading ? "Generating..." : markdown ? "Regenerate Markdown" : "Generate Markdown"}
        </button>
        {markdown ? (
          <>
            <button className="secondary-action" onClick={handleCopy} type="button">Copy</button>
            <button className="secondary-action" onClick={handleDownload} type="button">Download .md</button>
          </>
        ) : null}
      </div>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}
      {markdown ? (
        <textarea aria-label="Markdown export" readOnly rows={12} value={markdown} />
      ) : null}
    </section>
  );
}
