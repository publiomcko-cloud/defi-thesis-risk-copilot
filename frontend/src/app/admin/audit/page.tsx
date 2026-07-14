"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchAuditEvents } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";

export default function AuditEventsPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAuditEvents();
      setEvents(response.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audit events failed to load.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Audit Events</h1>
        <p>
          Review protected actions such as provider credential changes,
          discovery runs, review approvals, and explicit RAG ingestion.
        </p>
      </section>

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Recent Events</h2>
            <p>Sensitive metadata is redacted before it is stored.</p>
          </div>
          <div className="toolbar-actions">
            <button className="secondary-action" onClick={refresh} type="button">
              {loading ? "Loading..." : "Refresh"}
            </button>
            <Link className="secondary-link" href="/admin">
              Admin Home
            </Link>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Action</th>
                <th>Resource</th>
                <th>Actor</th>
                <th>Metadata</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5}>{loading ? "Loading audit events..." : "No audit events recorded."}</td>
                </tr>
              ) : (
                events.map((event) => (
                  <tr key={event.id}>
                    <td>
                      <strong>{event.action}</strong>
                      <span>{event.id}</span>
                    </td>
                    <td>
                      <strong>{event.resource_type}</strong>
                      <span>{event.resource_id ?? "none"}</span>
                    </td>
                    <td>{event.actor_user_id ?? "system"}</td>
                    <td>
                      <code>{JSON.stringify(event.metadata_json)}</code>
                    </td>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
