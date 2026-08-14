"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PublicAdminBoundary } from "@/components/PublicAdminBoundary";
import { fetchOperationsMonitoring } from "@/lib/api";
import type { OperationsMonitoring } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function OperationsAdminPage() {
  if (publicDemoMode) {
    return (
      <PublicAdminBoundary
        title="Operations signals are private"
        description="Aggregate queue, worker, retrieval, and readiness signals require an authenticated private deployment."
      />
    );
  }
  return <PrivateOperationsAdminPage />;
}

function PrivateOperationsAdminPage() {
  const [monitoring, setMonitoring] = useState<OperationsMonitoring | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      setMonitoring(await fetchOperationsMonitoring());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Operations signals failed to load.");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Operations</h1>
        <p>Aggregate-only readiness, queue, worker, and retrieval signals. No alert destination is configured here.</p>
      </section>

      <div className="stack">
        <section className="panel">
          <div className="section-toolbar">
            <div>
              <h2>Monitoring Snapshot</h2>
              <p>{monitoring ? `Checked ${new Date(monitoring.checked_at).toLocaleString()}` : "Loading current aggregate state."}</p>
            </div>
            <div className="action-row">
              <Link className="secondary-link" href="/admin">Admin Home</Link>
              <button className="secondary-action" onClick={() => void refresh()} type="button">Refresh</button>
            </div>
          </div>
          {error ? <p className="error">{error}</p> : null}
          {monitoring ? (
            <div className="meta-grid">
              <Metric label="Status" value={monitoring.status} />
              <Metric label="Monitoring" value={monitoring.monitoring_mode} />
              <Metric label="Alert delivery" value={monitoring.alert_delivery} />
              <Metric label="Database" value={String(monitoring.database_ready)} />
              <Metric label="JSON fallback" value={String(monitoring.json_fallback_ready)} />
              <Metric label="Knowledge storage" value={monitoring.knowledge_storage_state} />
            </div>
          ) : null}
        </section>

        {monitoring ? (
          <>
            <section className="panel">
              <h2>Queue and Workers</h2>
              <div className="meta-grid">
                <Metric label="Queued" value={String(monitoring.queue_depth)} />
                <Metric label="Oldest queue age" value={duration(monitoring.oldest_queue_age_seconds)} />
                <Metric label="Leased / Running" value={String(monitoring.leased_or_running_jobs)} />
                <Metric label="Dead letters" value={String(monitoring.dead_letter_jobs)} />
                <Metric label="Active workers" value={String(monitoring.active_workers)} />
                <Metric label="Stale workers" value={String(monitoring.stale_workers + monitoring.overdue_active_workers)} />
                <Metric label="Provider cleanup failures" value={String(monitoring.provider_cleanup_failures)} />
                <Metric label="Active schedules" value={String(monitoring.active_monitoring_schedules)} />
                <Metric label="Due schedules" value={String(monitoring.due_monitoring_schedules)} />
                <Metric label="Schedule dispatch" value={String(monitoring.schedule_dispatch_enabled)} />
              </div>
            </section>
            <section className="panel">
              <h2>Retrieval</h2>
              <div className="meta-grid">
                <Metric label="Events in window" value={String(monitoring.retrieval_events)} />
                <Metric label="Empty rate" value={percent(monitoring.retrieval_empty_rate_percent)} />
                <Metric label="Average latency" value={milliseconds(monitoring.retrieval_average_latency_ms)} />
                <Metric label="Max latency" value={milliseconds(monitoring.retrieval_max_latency_ms)} />
              </div>
            </section>
            <section className="panel">
              <h2>Local Alert Candidates</h2>
              {monitoring.alerts.length === 0 ? <p>No threshold candidate is active.</p> : (
                <ul className="stack-list">
                  {monitoring.alerts.map((alert) => <li key={alert.key}><strong>{alert.severity}</strong><span>{alert.summary}</span><span>{alert.runbook_id}</span></li>)}
                </ul>
              )}
            </section>
            <section className="panel">
              <h2>SLO Targets</h2>
              <div className="meta-grid">
                {Object.entries(monitoring.slo_targets).map(([label, value]) => <Metric key={label} label={label} value={value} />)}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function duration(seconds: number | null | undefined) {
  return seconds === null || seconds === undefined ? "No queued work" : `${seconds}s`;
}

function milliseconds(value: number | null | undefined) {
  return value === null || value === undefined ? "Not observed" : `${value}ms`;
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? "Not observed" : `${value}%`;
}
