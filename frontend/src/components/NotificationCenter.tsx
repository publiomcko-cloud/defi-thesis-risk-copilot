"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  fetchNotificationPreferences,
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  markNotificationUnread,
  updateNotificationPreferences
} from "@/lib/api";
import type {
  NotificationCategory,
  NotificationItem,
  NotificationPreferenceResponse,
  NotificationSeverity
} from "@/lib/types";

const categories: NotificationCategory[] = [
  "monitoring.risk_alert",
  "schedule.status",
  "job.status",
  "account.lifecycle"
];
const severities: NotificationSeverity[] = ["informational", "warning", "critical"];

export function NotificationCenter() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferenceResponse | null>(null);
  const [timezone, setTimezone] = useState("UTC");
  const [quietStart, setQuietStart] = useState("");
  const [quietEnd, setQuietEnd] = useState("");
  const [digest, setDigest] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [notificationResult, preferenceResult] = await Promise.all([
      fetchNotifications(),
      fetchNotificationPreferences()
    ]);
    setItems(notificationResult.items);
    setPreferences(preferenceResult);
    setTimezone(preferenceResult.timezone);
    setQuietStart(preferenceResult.quiet_hours_start ?? "");
    setQuietEnd(preferenceResult.quiet_hours_end ?? "");
    setDigest(preferenceResult.daily_digest_enabled);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh().catch((caught) => {
      setLoading(false);
      setError(caught instanceof Error ? caught.message : "Notifications could not be loaded.");
    });
  }, [refresh]);

  async function updateReadState(item: NotificationItem, read: boolean) {
    setActiveAction(`${read ? "read" : "unread"}:${item.id}`);
    setError(null);
    try {
      if (read) await markNotificationRead(item.id);
      else await markNotificationUnread(item.id);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Notification state could not be updated.");
    } finally {
      setActiveAction(null);
    }
  }

  async function markAllRead() {
    setActiveAction("mark-all");
    setError(null);
    try {
      await markAllNotificationsRead();
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Notifications could not be marked read.");
    } finally {
      setActiveAction(null);
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preferences) return;
    setActiveAction("preferences");
    setError(null);
    setMessage(null);
    try {
      const updated = await updateNotificationPreferences({
        categories: preferences.categories,
        minimum_severity: preferences.minimum_severity,
        timezone,
        quiet_hours_start: quietStart || null,
        quiet_hours_end: quietEnd || null,
        daily_digest_enabled: digest
      });
      setPreferences(updated);
      setMessage("Notification preferences saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Notification preferences could not be saved.");
    } finally {
      setActiveAction(null);
    }
  }

  if (loading) {
    return <section className="panel" aria-busy="true"><h2>Notifications</h2><p>Loading notifications...</p></section>;
  }

  if (error && !preferences) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Notifications are private to your account.</p>
        <Link className="primary-link" href="/login">Log in</Link>
      </section>
    );
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Recent Notifications</h2>
            <p>Only server-owned notification intents are shown here.</p>
          </div>
          <div className="action-row compact-actions">
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void refresh()} type="button">Refresh</button>
            <button className="secondary-action" disabled={activeAction !== null || !items.some((item) => !item.read_at)} onClick={() => void markAllRead()} type="button">
              {activeAction === "mark-all" ? "Updating..." : "Mark all read"}
            </button>
          </div>
        </div>
        {error ? <p className="error" role="alert">{error}</p> : null}
        {!items.length ? <p>No notifications are available.</p> : null}
        <div className="notification-list" role="list">
          {items.map((item) => (
            <article className={`notification-row ${item.read_at ? "is-read" : "is-unread"}`} key={item.id} role="listitem">
              <div>
                <div className="notification-meta">
                  <span className={`job-status severity-${item.severity}`}>{item.severity}</span>
                  <span>{item.category}</span>
                  <time>{formatTime(item.created_at)}</time>
                </div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </div>
              <div className="action-row compact-actions">
                {safePath(item.navigation.path) ? <Link className="primary-link" href={item.navigation.path as string}>Open</Link> : null}
                <button className="secondary-action" disabled={activeAction !== null} onClick={() => void updateReadState(item, !item.read_at)} type="button">
                  {activeAction?.endsWith(item.id) ? "Updating..." : item.read_at ? "Mark unread" : "Mark read"}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {preferences ? (
        <form className="form-panel" onSubmit={savePreferences}>
          <div className="section-toolbar">
            <div>
              <h2>Preferences</h2>
              <p>Security and account lifecycle notifications cannot be suppressed.</p>
            </div>
          </div>
          <div className="preferences-grid">
            {categories.map((category) => {
              const mandatory = preferences.mandatory_categories.includes(category);
              return (
                <fieldset key={category}>
                  <legend>{category}</legend>
                  <label className="inline-field">
                    <input
                      checked={preferences.categories[category]}
                      disabled={mandatory || activeAction !== null}
                      onChange={(event) => setPreferences({
                        ...preferences,
                        categories: { ...preferences.categories, [category]: event.target.checked }
                      })}
                      type="checkbox"
                    />
                    Enabled
                  </label>
                  <label>
                    Minimum severity
                    <select
                      disabled={activeAction !== null}
                      onChange={(event) => setPreferences({
                        ...preferences,
                        minimum_severity: { ...preferences.minimum_severity, [category]: event.target.value as NotificationSeverity }
                      })}
                      value={preferences.minimum_severity[category]}
                    >
                      {severities.map((severity) => <option key={severity} value={severity}>{severity}</option>)}
                    </select>
                  </label>
                </fieldset>
              );
            })}
          </div>
          <div className="manual-grid">
            <label>
              Timezone
              <input disabled={activeAction !== null} maxLength={64} onChange={(event) => setTimezone(event.target.value)} value={timezone} />
            </label>
            <label>
              Quiet start
              <input disabled={activeAction !== null} onChange={(event) => setQuietStart(event.target.value)} pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$" placeholder="22:00" value={quietStart} />
            </label>
            <label>
              Quiet end
              <input disabled={activeAction !== null} onChange={(event) => setQuietEnd(event.target.value)} pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$" placeholder="07:00" value={quietEnd} />
            </label>
            <label className="inline-field">
              <input checked={digest} disabled={activeAction !== null} onChange={(event) => setDigest(event.target.checked)} type="checkbox" />
              Daily digest
            </label>
          </div>
          {message ? <p className="success" role="status">{message}</p> : null}
          <button className="primary-action" disabled={activeAction !== null} type="submit">
            {activeAction === "preferences" ? "Saving..." : "Save preferences"}
          </button>
        </form>
      ) : null}
    </div>
  );
}

function safePath(path: string | undefined): boolean {
  return Boolean(path?.startsWith("/") && !path.includes("//") && !path.includes(".."));
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}
