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
  const [consents, setConsents] = useState<Array<{ document_type: string; document_version: string; accepted_at: string; withdrawn_at?: string | null }>>([]);
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
    fetch("/api/backend/api/consents", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { items: [] }))
      .then((payload) => setConsents(payload.items ?? []))
      .catch(() => setConsents([]));
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    setSession({ authenticated: false });
    window.dispatchEvent(new Event("defi-session-changed"));
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
    const confirmation = window.prompt("Type DELETE to request account deletion.");
    if (confirmation !== "DELETE") {
      setMessage("Account deletion was not confirmed.");
      return;
    }
    const response = await fetch("/api/backend/api/account", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "DELETE" })
    });
    setMessage(response.ok ? "Account deletion requested." : "Account deletion could not be completed.");
  }

  async function acceptConsent(documentType: "terms" | "privacy") {
    const response = await fetch("/api/backend/api/consents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_type: documentType })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      setMessage(payload.detail ?? "Consent could not be recorded.");
      return;
    }
    const consent = payload.consent;
    setConsents((current) => [
      ...current.filter((item) => item.document_type !== consent.document_type),
      consent
    ]);
    setMessage(`${documentType === "terms" ? "Terms" : "Privacy policy"} consent recorded.`);
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
        {message ? <p className="form-success">{message}</p> : null}
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
        <h2>Consent</h2>
        {consents.length ? (
          <ul className="compact-list">
            {consents.map((consent) => (
              <li key={`${consent.document_type}-${consent.document_version}`}>
                {consent.document_type} {consent.document_version} accepted
              </li>
            ))}
          </ul>
        ) : <p>No current consent records.</p>}
        <div className="action-row compact-actions">
          <button className="secondary-action" onClick={() => void acceptConsent("terms")} type="button">Accept terms</button>
          <button className="secondary-action" onClick={() => void acceptConsent("privacy")} type="button">Accept privacy</button>
        </div>
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
