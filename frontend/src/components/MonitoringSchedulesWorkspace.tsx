"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  createMonitoringSchedule,
  deleteMonitoringSchedule,
  fetchMonitoringScheduleRuns,
  fetchMonitoringSchedules,
  fetchWatchlistItems,
  pauseMonitoringSchedule,
  resumeMonitoringSchedule
} from "@/lib/api";
import type {
  MonitoringSchedule,
  MonitoringScheduleCadence,
  MonitoringScheduleRun,
  WatchlistItem
} from "@/lib/types";

const cadenceLabels: Record<MonitoringScheduleCadence, string> = {
  hourly: "Hourly",
  six_hourly: "Every six hours",
  daily: "Daily",
  weekly: "Weekly"
};

export function MonitoringSchedulesWorkspace() {
  const [schedules, setSchedules] = useState<MonitoringSchedule[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [dispatchEnabled, setDispatchEnabled] = useState(false);
  const [targetId, setTargetId] = useState("");
  const [cadence, setCadence] = useState<MonitoringScheduleCadence>("daily");
  const [timezone, setTimezone] = useState("UTC");
  const [runs, setRuns] = useState<Record<string, MonitoringScheduleRun[]>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [scheduleResult, watchlistResult] = await Promise.all([
      fetchMonitoringSchedules(),
      fetchWatchlistItems()
    ]);
    setSchedules(scheduleResult.items);
    setDispatchEnabled(scheduleResult.dispatch_enabled);
    setWatchlist(watchlistResult.items.filter((item) => item.enabled));
    setTargetId((current) => current || watchlistResult.items.find((item) => item.enabled)?.id || "");
  }, []);

  useEffect(() => {
    try {
      setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
    } catch {
      setTimezone("UTC");
    }
    void refresh().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Monitoring schedules could not be loaded.");
    });
  }, [refresh]);

  async function createSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveAction("create");
    setError(null);
    setMessage(null);
    try {
      await createMonitoringSchedule({
        target_type: "watchlist.evaluate",
        target_id: targetId,
        cadence,
        timezone
      });
      setMessage("Monitoring schedule created.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Monitoring schedule could not be created.");
    } finally {
      setActiveAction(null);
    }
  }

  async function changeSchedule(schedule: MonitoringSchedule, action: "pause" | "resume" | "delete") {
    setActiveAction(`${action}:${schedule.id}`);
    setError(null);
    setMessage(null);
    try {
      if (action === "pause") await pauseMonitoringSchedule(schedule.id);
      if (action === "resume") await resumeMonitoringSchedule(schedule.id);
      if (action === "delete") await deleteMonitoringSchedule(schedule.id);
      setMessage(`Monitoring schedule ${action === "delete" ? "deleted" : `${action}d`}.`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Monitoring schedule could not be updated.");
    } finally {
      setActiveAction(null);
    }
  }

  async function toggleRuns(scheduleId: string) {
    if (expandedId === scheduleId) {
      setExpandedId(null);
      return;
    }
    setActiveAction(`runs:${scheduleId}`);
    try {
      const result = await fetchMonitoringScheduleRuns(scheduleId);
      setRuns((current) => ({ ...current, [scheduleId]: result.items }));
      setExpandedId(scheduleId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Schedule history could not be loaded.");
    } finally {
      setActiveAction(null);
    }
  }

  if (error && !schedules.length && !watchlist.length) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Monitoring schedules are private to your account.</p>
        <Link className="primary-link" href="/login">Log in</Link>
      </section>
    );
  }

  return (
    <div className="stack">
      <section className="notice">
        <h2>Controlled monitoring</h2>
        <p>
          Schedules evaluate only your enabled private watchlist items. They do not execute trades or send external notifications.
        </p>
        <p>{dispatchEnabled ? "Automatic dispatch is enabled for this environment." : "Automatic dispatch is unavailable for this deployment; schedule history remains preserved."}</p>
      </section>

      <form className="form-panel" onSubmit={createSchedule}>
        <div className="section-toolbar">
          <div>
            <h2>New Schedule</h2>
            <p>Execution time, ownership, quotas, and job inputs are derived on the server.</p>
          </div>
        </div>
        <div className="manual-grid">
          <label>
            Watchlist item
            <select disabled={!watchlist.length || activeAction !== null} onChange={(event) => setTargetId(event.target.value)} value={targetId}>
              {!watchlist.length ? <option value="">Create an enabled watchlist item first</option> : null}
              {watchlist.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
            </select>
          </label>
          <label>
            Cadence
            <select disabled={activeAction !== null} onChange={(event) => setCadence(event.target.value as MonitoringScheduleCadence)} value={cadence}>
              {Object.entries(cadenceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            Timezone
            <input aria-describedby="timezone-help" disabled={activeAction !== null} maxLength={64} onChange={(event) => setTimezone(event.target.value)} value={timezone} />
            <span className="field-help" id="timezone-help">Use an IANA timezone, for example America/Sao_Paulo.</span>
          </label>
        </div>
        {error ? <p className="error" role="alert">{error}</p> : null}
        {message ? <p className="success" role="status">{message}</p> : null}
        <button className="primary-action" disabled={!targetId || activeAction !== null} type="submit">
          {activeAction === "create" ? "Creating..." : "Create schedule"}
        </button>
      </form>

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Your Schedules</h2>
            <p>Missed work is coalesced safely; runs more than 24 hours late are recorded as skipped.</p>
          </div>
          <button className="secondary-action" disabled={activeAction !== null} onClick={() => void refresh().catch((caught) => setError(caught instanceof Error ? caught.message : "Refresh failed."))} type="button">Refresh</button>
        </div>
        {error ? <p className="error" role="alert">{error}</p> : null}
        {!schedules.length ? <p>No monitoring schedules yet.</p> : null}
        <div className="table-wrap">
          <table>
            <thead><tr><th>Target</th><th>Cadence</th><th>Next due</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {schedules.map((schedule) => (
                <ScheduleRow
                  activeAction={activeAction}
                  key={schedule.id}
                  onChange={changeSchedule}
                  onRuns={toggleRuns}
                  runs={expandedId === schedule.id ? runs[schedule.id] : undefined}
                  schedule={schedule}
                />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function ScheduleRow({
  activeAction,
  onChange,
  onRuns,
  runs,
  schedule
}: {
  activeAction: string | null;
  onChange: (schedule: MonitoringSchedule, action: "pause" | "resume" | "delete") => Promise<void>;
  onRuns: (scheduleId: string) => Promise<void>;
  runs?: MonitoringScheduleRun[];
  schedule: MonitoringSchedule;
}) {
  return (
    <>
      <tr>
        <td><code>{schedule.target_id}</code></td>
        <td>{cadenceLabels[schedule.cadence]}<span>{schedule.timezone}</span></td>
        <td>{formatDate(schedule.next_due_at)}</td>
        <td><span className={`job-status job-status-${schedule.status}`}>{schedule.status}</span></td>
        <td>
          <div className="action-row compact-actions">
            {schedule.status === "active" ? <button className="secondary-action" disabled={activeAction !== null} onClick={() => void onChange(schedule, "pause")} type="button">Pause</button> : null}
            {schedule.status === "paused" ? <button className="secondary-action" disabled={activeAction !== null} onClick={() => void onChange(schedule, "resume")} type="button">Resume</button> : null}
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void onRuns(schedule.id)} type="button">{activeAction === `runs:${schedule.id}` ? "Loading..." : runs ? "Hide runs" : "Runs"}</button>
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void onChange(schedule, "delete")} type="button">Delete</button>
          </div>
        </td>
      </tr>
      {runs ? <tr><td colSpan={5}><ScheduleRuns runs={runs} /></td></tr> : null}
    </>
  );
}

function ScheduleRuns({ runs }: { runs: MonitoringScheduleRun[] }) {
  if (!runs.length) return <p className="muted-small">No runs have been recorded yet.</p>;
  return <ul className="compact-list">
    {runs.map((run) => <li key={run.id}><strong>{formatDate(run.scheduled_for)}</strong>: {run.status}{run.reason ? ` (${run.reason.replaceAll("_", " ")})` : ""}{run.job_id ? ` · job ${run.job_id}` : ""}</li>)}
  </ul>;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}
