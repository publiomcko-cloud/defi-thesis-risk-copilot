"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PublicAdminBoundary } from "@/components/PublicAdminBoundary";
import { fetchAuditEvents } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function AuditEventsPage() {
  if (publicDemoMode) {
    return (
      <PublicAdminBoundary
        title="Audit events are private"
        description="Operational audit records are available only to authenticated administrators in a private deployment."
      />
    );
  }

  return <PrivateAuditEvents />;
}

function PrivateAuditEvents() {
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
        <p>Review protected credential, discovery, review, RAG, and infrastructure actions.</p>
      </section>

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Recent Events</h2>
            <p>Sensitive metadata is redacted before storage.</p>
          </div>
          <div className="toolbar-actions">
            <button className="secondary-action" onClick={refresh} type="button">
              {loading ? "Loading..." : "Refresh"}
            </button>
            <Link className="secondary-link" href="/admin">Admin Home</Link>
          </div>
        </div>
        {error ? <p className="error">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Action</th><th>Resource</th><th>Actor</th><th>Metadata</th><th>Created</th></tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr><td colSpan={5}>{loading ? "Loading audit events..." : "No audit events recorded."}</td></tr>
              ) : events.map((event) => (
                <tr key={event.id}>
                  <td><strong>{event.action}</strong><span>{event.id}</span></td>
                  <td><strong>{event.resource_type}</strong><span>{event.resource_id ?? "none"}</span></td>
                  <td>{event.actor_user_id ?? "system"}</td>
                  <td><code>{JSON.stringify(event.metadata_json)}</code></td>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
