"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type SessionPayload = {
  authenticated: boolean;
  user?: {
    email: string;
    plan?: string;
    platform_role?: string;
  };
};

export function AccountPanel() {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [usage, setUsage] = useState<{ items: Array<{ action: string; used: number; limit: number; remaining: number }> } | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.json())
      .then(setSession)
      .catch(() => setSession({ authenticated: false }));
    fetch("/api/backend/api/usage", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then(setUsage)
      .catch(() => setUsage(null));
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    setSession({ authenticated: false });
    setMessage("Signed out.");
  }

  async function exportAccount() {
    const response = await fetch("/api/backend/api/account/export", { cache: "no-store" });
    if (!response.ok) {
      setMessage("Account export is available after login.");
      return;
    }
    const blob = new Blob([JSON.stringify(await response.json(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "defi-copilot-account-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function deleteAccount() {
    const confirmed = window.confirm("Type-level confirmation is required. Continue with account deletion request?");
    if (!confirmed) {
      return;
    }
    const response = await fetch("/api/backend/api/account", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "DELETE" })
    });
    setMessage(response.ok ? "Account deletion requested." : "Account deletion could not be completed.");
  }

  if (session === null) {
    return <section className="panel loading-panel">Loading account...</section>;
  }

  if (!session.authenticated) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Private account data is available after login.</p>
        <Link className="primary-link" href="/login">Log in</Link>
      </section>
    );
  }

  return (
    <section className="content-grid">
      <article className="panel">
        <h2>Profile</h2>
        <p>{session.user?.email}</p>
        <p>Plan: {session.user?.plan ?? "free"}</p>
        <p>Platform role: {session.user?.platform_role ?? "user"}</p>
        <div className="action-row compact-actions">
          <button className="secondary-action" onClick={exportAccount} type="button">Export</button>
          <button className="secondary-action" onClick={logout} type="button">Logout</button>
          <button className="secondary-action" onClick={deleteAccount} type="button">Delete</button>
        </div>
      </article>
      <article className="panel">
        <h2>Security</h2>
        <p>MFA is optional for ordinary users and can be required for platform administrators.</p>
        <Link className="secondary-link" href="/account/security">Open security</Link>
      </article>
      <article className="panel">
        <h2>Usage</h2>
        {usage?.items.length ? (
          <ul className="compact-list">
            {usage.items.map((item) => (
              <li key={item.action}>{item.action}: {item.used}/{item.limit} used, {item.remaining} remaining</li>
            ))}
          </ul>
        ) : (
          <p>No quota usage recorded yet.</p>
        )}
      </article>
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
