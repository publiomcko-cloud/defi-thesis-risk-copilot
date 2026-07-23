"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DisclaimerBox } from "@/components/DisclaimerBox";
import { fetchCurrentUser } from "@/lib/api";
import type { UserContext } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function AdminPage() {
  const [currentUser, setCurrentUser] = useState<UserContext | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (publicDemoMode) {
      return;
    }
    void refreshUser();
  }, []);

  async function refreshUser() {
    setError(null);
    try {
      const user = await fetchCurrentUser();
      setCurrentUser(user);
    } catch (caught) {
      setCurrentUser(null);
      setError(caught instanceof Error ? caught.message : "Unable to load auth state.");
    }
  }

  if (publicDemoMode) {
    return (
      <main className="page narrow-page">
        <section className="page-heading">
          <p className="eyebrow">Protected product area</p>
          <h1>Admin tools are not exposed publicly</h1>
          <p>
            Credentials, audit logs, review mutations, RAG ingestion, and Vast.ai
            lifecycle controls require an authenticated private deployment.
          </p>
        </section>
        <section className="notice">
          <h2>Public read-only boundary</h2>
          <p>
            The portfolio deployment intentionally shows the product workflow without
            granting visitors administrative identity or mutation access.
          </p>
        </section>
        <div className="action-row">
          <Link className="primary-link" href="/demo">Return to Demo</Link>
          <Link className="secondary-link" href="/review">View Read-Only Review Flow</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Access control</p>
        <h1>Admin</h1>
        <p>
          Configure provider credentials, check the current role, and review audit
          events for protected workflows.
        </p>
      </section>

      <div className="stack">
        <section className="panel">
          <h2>Session</h2>
          <div className="action-row">
            <button className="secondary-action" onClick={refreshUser} type="button">
              Check Role
            </button>
            <Link className="primary-link" href="/login">Log in</Link>
          </div>
          {error ? <p className="error">{error}</p> : null}
          {currentUser ? (
            <div className="meta-grid">
              <div>
                <span>Auth mode</span>
                <strong>{currentUser.auth_enabled ? "Enabled" : "Local disabled mode"}</strong>
              </div>
              <div>
                <span>User</span>
                <strong>{currentUser.email}</strong>
              </div>
              <div>
                <span>Role</span>
                <strong>{currentUser.role}</strong>
              </div>
            </div>
          ) : null}
        </section>

        <section className="panel">
          <h2>Protected Tools</h2>
          <div className="action-row">
            <Link className="secondary-link" href="/admin/provider-credentials">Provider Credentials</Link>
            <Link className="secondary-link" href="/admin/audit">Audit Events</Link>
            <Link className="secondary-link" href="/admin/vast">Vast.ai</Link>
            <Link className="secondary-link" href="/review">Review Queue</Link>
          </div>
        </section>
      </div>

      <DisclaimerBox text="Access control protects configuration and review actions. The app still does not connect wallets, custody assets, execute trades, or produce buy/sell recommendations." />
    </main>
  );
}
