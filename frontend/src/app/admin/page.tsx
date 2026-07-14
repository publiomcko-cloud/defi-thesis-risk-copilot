"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DisclaimerBox } from "@/components/DisclaimerBox";
import { fetchCurrentUser, getAuthToken, setAuthToken } from "@/lib/api";
import type { UserContext } from "@/lib/types";

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [currentUser, setCurrentUser] = useState<UserContext | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = getAuthToken();
    setToken(savedToken);
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

  async function handleSaveToken() {
    setAuthToken(token);
    setMessage(token.trim() ? "Admin token saved for this browser." : "Admin token cleared.");
    await refreshUser();
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Access control</p>
        <h1>Admin</h1>
        <p>
          Configure provider credentials, check the current role, and review
          audit events for protected workflows.
        </p>
      </section>

      <div className="stack">
        <section className="panel">
          <h2>Session</h2>
          <div className="manual-grid">
            <label>
              Admin bearer token
              <input
                autoComplete="off"
                onChange={(event) => setToken(event.target.value)}
                placeholder="Only needed when AUTH_ENABLED=true"
                type="password"
                value={token}
              />
            </label>
          </div>
          <div className="action-row">
            <button className="primary-action" onClick={handleSaveToken} type="button">
              Save Token
            </button>
            <button className="secondary-action" onClick={refreshUser} type="button">
              Check Role
            </button>
          </div>
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
          {currentUser ? (
            <div className="meta-grid">
              <div>
                <span>Auth mode</span>
                <strong>{currentUser.auth_enabled ? "Enabled" : "Demo disabled mode"}</strong>
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
            <Link className="secondary-link" href="/admin/provider-credentials">
              Provider Credentials
            </Link>
            <Link className="secondary-link" href="/admin/audit">
              Audit Events
            </Link>
            <Link className="secondary-link" href="/review">
              Review Queue
            </Link>
          </div>
        </section>
      </div>

      <DisclaimerBox text="Access control protects configuration and review actions. The app still does not connect wallets, custody assets, execute trades, or produce buy/sell recommendations." />
    </main>
  );
}
