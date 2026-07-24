"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { cancelJob, fetchJobEvents, fetchJobs } from "@/lib/api";
import type { JobEvent, JobResponse } from "@/lib/types";

const activeStatuses = new Set(["queued", "leased", "running", "retry_wait", "cancel_requested"]);
const cancellableStatuses = new Set(["queued", "leased", "running", "retry_wait"]);

export function JobsWorkspace() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [eventsByJob, setEventsByJob] = useState<Record<string, JobEvent[]>>({});
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetchJobs();
      setJobs(response.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Jobs could not be loaded.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!jobs.some((job) => activeStatuses.has(job.status))) {
      return;
    }
    const interval = window.setInterval(() => void refresh(), 4_000);
    return () => window.clearInterval(interval);
  }, [jobs, refresh]);

  async function toggleDetails(jobId: string) {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      return;
    }
    setActiveAction(`events:${jobId}`);
    try {
      const response = await fetchJobEvents(jobId);
      setEventsByJob((current) => ({ ...current, [jobId]: response.items }));
      setExpandedJobId(jobId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Job events could not be loaded.");
    } finally {
      setActiveAction(null);
    }
  }

  async function requestCancellation(jobId: string) {
    setActiveAction(`cancel:${jobId}`);
    try {
      await cancelJob(jobId);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Cancellation could not be requested.");
    } finally {
      setActiveAction(null);
    }
  }

  if (error && jobs.length === 0) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Private job history is available after login.</p>
        <Link className="primary-link" href="/login">Log in</Link>
      </section>
    );
  }

  return (
    <section className="stack">
      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Recent Jobs</h2>
            <p>Active jobs refresh automatically while they are waiting or running.</p>
          </div>
          <button className="secondary-action" disabled={activeAction !== null} onClick={() => void refresh()} type="button">Refresh</button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {!jobs.length ? <p>No private jobs have been submitted.</p> : null}
      </section>

      {jobs.map((job) => (
        <article className="panel job-panel" key={job.id}>
          <div className="section-toolbar">
            <div>
              <p className="eyebrow">{job.job_type}</p>
              <h2>{job.id}</h2>
              <p>{jobMessage(job)}</p>
            </div>
            <span className={`job-status job-status-${job.status}`}>{job.status.replaceAll("_", " ")}</span>
          </div>
          <div className="job-progress" aria-label={`Progress for ${job.id}`}>
            <span style={{ width: `${job.progress_percent}%` }} />
          </div>
          <div className="job-meta-grid">
            <span>Progress<strong>{job.progress_percent}%</strong></span>
            <span>Attempts<strong>{job.attempt_count}/{job.max_attempts}</strong></span>
            <span>Submitted<strong>{formatTime(job.created_at)}</strong></span>
            <span>Updated<strong>{formatTime(job.updated_at)}</strong></span>
          </div>
          {job.error_summary ? <p className="error-text">{job.error_summary}</p> : null}
          {job.status === "dead_letter" || job.status === "failed" ? <p className="notice-text">This job needs an administrator review before it can be replayed.</p> : null}
          <div className="action-row compact-actions">
            {job.status === "completed" && job.result_resource_type === "report" && job.result_resource_id ? (
              <Link className="primary-link" href={`/reports/${job.result_resource_id}`}>Open report</Link>
            ) : null}
            {job.result_resource_type && job.result_resource_id && job.result_resource_type !== "report" ? (
              <span className="result-reference">Result: {job.result_resource_type} · {job.result_resource_id}</span>
            ) : null}
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void toggleDetails(job.id)} type="button">
              {activeAction === `events:${job.id}` ? "Loading..." : expandedJobId === job.id ? "Hide details" : "Details"}
            </button>
            {cancellableStatuses.has(job.status) ? (
              <button className="secondary-action" disabled={activeAction !== null} onClick={() => void requestCancellation(job.id)} type="button">
                {activeAction === `cancel:${job.id}` ? "Cancelling..." : "Cancel job"}
              </button>
            ) : null}
          </div>
          {expandedJobId === job.id ? <JobEvents events={eventsByJob[job.id] ?? []} /> : null}
        </article>
      ))}
    </section>
  );
}

function JobEvents({ events }: { events: JobEvent[] }) {
  if (!events.length) {
    return <p className="muted-small">No durable events recorded yet.</p>;
  }
  return (
    <ol className="job-events">
      {events.map((event) => <li key={event.id}><strong>{event.event_type}</strong><span>{event.message}</span><time>{formatTime(event.created_at)}</time></li>)}
    </ol>
  );
}

function jobMessage(job: JobResponse): string {
  if (job.progress_message) return job.progress_message;
  if (job.status === "queued") return "Waiting for an eligible worker.";
  if (job.status === "cancel_requested") return "Cancellation has been requested and is waiting for the worker.";
  if (job.status === "leased") return "A worker holds the lease and is preparing controlled execution.";
  if (job.status === "running") return "A worker is executing under an active lease.";
  if (job.status === "failed" && job.error_code === "authorization_revoked") return "Authorization changed before this job could complete.";
  if (job.status === "failed" && job.error_code === "queue_expired") return "The queue deadline elapsed before a worker accepted this job.";
  if (job.status === "dead_letter") return "The job reached its final attempt and needs administrator review.";
  if (job.status === "retry_wait") return "The worker recorded a retryable issue; the next controlled attempt will wait for its backoff window.";
  if (job.status === "completed") return "Completed.";
  if (job.status === "cancelled") return "Cancelled.";
  return "Worker state is being recorded.";
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}
