"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  evaluateDiscoveredItem,
  fetchDiscoveredItems,
  fetchReviewItems,
  ingestReviewItemToRag,
  runDiscovery,
  runSourceMonitoring,
  updateReviewItemStatus
} from "@/lib/api";
import type { DiscoveredItem, ReviewItem, ReviewStatus } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

const reviewStatuses: ReviewStatus[] = [
  "needs_review",
  "approved_for_rag",
  "needs_more_data",
  "rejected",
  "archived"
];

export function ReviewQueueTable() {
  const [discoveredItems, setDiscoveredItems] = useState<DiscoveredItem[]>([]);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reviewerNotes, setReviewerNotes] = useState<Record<string, string>>({});

  const evaluatedIds = useMemo(
    () => new Set(reviewItems.map((item) => item.discovered_item_id)),
    [reviewItems]
  );

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setError(null);
    try {
      const [discovered, reviews] = await Promise.all([
        fetchDiscoveredItems(),
        fetchReviewItems()
      ]);
      setDiscoveredItems(discovered.items);
      setReviewItems(reviews.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review data failed to load.");
    }
  }

  async function handleRunMonitoring() {
    setActiveId("monitoring");
    setMessage(null);
    setError(null);
    try {
      const result = await runSourceMonitoring();
      setMessage(
        `Monitoring checked ${result.watches_checked} watches: ${result.created_count} new, ${result.duplicate_count} duplicates, ${result.failed_count} failures.`
      );
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Monitoring run failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleRunDiscovery() {
    setActiveId("discovery");
    setMessage(null);
    setError(null);
    try {
      const result = await runDiscovery();
      setMessage(
        `Discovery found ${result.created_count} new candidates, ${result.duplicate_count} duplicates, evaluated ${result.evaluated_count}, and recorded ${result.failed_count} failures.`
      );
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Discovery run failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleEvaluate(itemId: string) {
    setActiveId(itemId);
    setMessage(null);
    setError(null);
    try {
      await evaluateDiscoveredItem(itemId);
      setMessage("Evaluation completed and queued for review.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evaluation failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleStatusChange(reviewItemId: string, status: ReviewStatus) {
    setActiveId(reviewItemId);
    setMessage(null);
    setError(null);
    try {
      await updateReviewItemStatus(reviewItemId, status, reviewerNotes[reviewItemId]);
      setMessage(
        status === "approved_for_rag"
          ? "Item approved for RAG. It was not ingested automatically; use the explicit ingest action."
          : "Review status updated."
      );
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Review update failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleIngestToRag(reviewItemId: string) {
    setActiveId(`ingest:${reviewItemId}`);
    setMessage(null);
    setError(null);
    try {
      const result = await ingestReviewItemToRag(reviewItemId);
      setMessage(
        `Ingested to RAG at ${result.ingestion.generated_markdown_path}. Refreshed ${result.refreshed_chunk_count} chunks.`
      );
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "RAG ingestion failed.");
    } finally {
      setActiveId(null);
    }
  }

  return (
    <div className="stack">
      {publicDemoMode ? (
        <section className="notice">
          <h2>Human-review workflow preview</h2>
          <p>
            This page shows seeded candidates and review outcomes. Monitoring,
            discovery, evaluation, status changes, and RAG ingestion are disabled in
            the public deployment so visitors cannot alter the shared knowledge base.
          </p>
        </section>
      ) : null}

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Discovered Candidates</h2>
            <p>
              Discovery creates candidates for evaluation and human review. Approval
              never triggers ingestion automatically.
            </p>
          </div>
          <div className="toolbar-actions">
            <button className="secondary-action" onClick={() => void refresh()} type="button">
              Refresh
            </button>
            {!publicDemoMode ? (
              <>
                <button
                  className="secondary-action"
                  disabled={activeId !== null}
                  onClick={handleRunMonitoring}
                  type="button"
                >
                  {activeId === "monitoring" ? "Running..." : "Run Monitoring"}
                </button>
                <button
                  className="primary-action"
                  disabled={activeId !== null}
                  onClick={handleRunDiscovery}
                  type="button"
                >
                  {activeId === "discovery" ? "Discovering..." : "Run Discovery"}
                </button>
              </>
            ) : null}
          </div>
        </div>
        {message ? <p className="success">{message}</p> : null}
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Source</th>
                <th>Status</th>
                {!publicDemoMode ? <th>Action</th> : null}
              </tr>
            </thead>
            <tbody>
              {discoveredItems.length === 0 ? (
                <tr>
                  <td colSpan={publicDemoMode ? 3 : 4}>No candidates discovered yet.</td>
                </tr>
              ) : (
                discoveredItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.title}</strong>
                      <span>{item.protocol ?? "unknown protocol"}</span>
                      {item.url ? (
                        <a className="text-link" href={item.url} rel="noreferrer" target="_blank">
                          Open source
                        </a>
                      ) : null}
                    </td>
                    <td>
                      <span>{humanize(item.source)}</span>
                      <span>{humanize(item.source_type)}</span>
                    </td>
                    <td><StatusBadge status={item.status} /></td>
                    {!publicDemoMode ? (
                      <td>
                        <button
                          className="secondary-action"
                          disabled={activeId !== null || evaluatedIds.has(item.id)}
                          onClick={() => handleEvaluate(item.id)}
                          type="button"
                        >
                          {activeId === item.id
                            ? "Evaluating..."
                            : evaluatedIds.has(item.id)
                              ? "Queued"
                              : "Evaluate"}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Review Queue</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Risk Summary</th>
                <th>Status</th>
                <th>Reviewer Notes</th>
                <th>RAG Ingestion</th>
              </tr>
            </thead>
            <tbody>
              {reviewItems.length === 0 ? (
                <tr>
                  <td colSpan={5}>No evaluated items are queued yet.</td>
                </tr>
              ) : (
                reviewItems.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.discovered_item.title}</strong>
                      <span>{item.discovered_item.protocol ?? "unknown protocol"}</span>
                      <Link className="text-link" href={`/reports/${item.evaluation_result.report_id}`}>
                        Open full report
                      </Link>
                    </td>
                    <td>
                      <p>{item.evaluation_result.risk_summary}</p>
                      <span>
                        Score {item.evaluation_result.risk_score} · {item.evaluation_result.risk_rating} · confidence {item.evaluation_result.confidence}
                      </span>
                    </td>
                    <td>
                      {publicDemoMode ? (
                        <StatusBadge status={item.status} />
                      ) : (
                        <select
                          disabled={activeId !== null}
                          onChange={(event) =>
                            handleStatusChange(item.id, event.target.value as ReviewStatus)
                          }
                          value={item.status}
                        >
                          {reviewStatuses.map((status) => (
                            <option key={status} value={status}>
                              {humanize(status)}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      {publicDemoMode ? (
                        <p>{item.reviewer_notes || "No reviewer note recorded."}</p>
                      ) : (
                        <textarea
                          aria-label={`Reviewer notes for ${item.discovered_item.title}`}
                          onChange={(event) =>
                            setReviewerNotes((current) => ({
                              ...current,
                              [item.id]: event.target.value
                            }))
                          }
                          placeholder="Optional review note"
                          rows={3}
                          value={reviewerNotes[item.id] ?? item.reviewer_notes ?? ""}
                        />
                      )}
                    </td>
                    <td>
                      {item.knowledge_base_ingestion ? (
                        <div>
                          <strong>Ingested</strong>
                          <span>{item.knowledge_base_ingestion.generated_markdown_path}</span>
                        </div>
                      ) : item.status === "approved_for_rag" && !publicDemoMode ? (
                        <button
                          className="secondary-action"
                          disabled={activeId !== null}
                          onClick={() => handleIngestToRag(item.id)}
                          type="button"
                        >
                          {activeId === `ingest:${item.id}` ? "Ingesting..." : "Ingest to RAG"}
                        </button>
                      ) : item.prepared_for_rag ? (
                        "Prepared for controlled ingestion"
                      ) : (
                        "Not eligible"
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{humanize(status)}</span>;
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
