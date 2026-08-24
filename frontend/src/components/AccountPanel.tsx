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

type AnalyticsPreference = {
  purpose: "product_improvement";
  enabled: boolean;
  policy_version: string;
  collection_enabled: boolean;
  requires_reconsent: boolean;
  updated_at?: string | null;
};

type Entitlements = {
  plan: string;
  version: number;
  provenance: string;
  limits: Record<string, number>;
  shadow: "parity" | "mismatch";
  comparisons: Array<{ key: string; result: "parity" | "mismatch" | "fallback"; legacy_limit: number; entitlement_limit: number | null }>;
  completed_usage: Record<string, number>;
};

export function AccountPanel() {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [usage, setUsage] = useState<{ items: Array<{ action: string; used: number; limit: number; remaining: number }> } | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [consents, setConsents] = useState<Array<{ document_type: string; document_version: string; accepted_at: string; withdrawn_at?: string | null }>>([]);
  const [analyticsPreference, setAnalyticsPreference] = useState<AnalyticsPreference | null>(null);
  const [analyticsUpdating, setAnalyticsUpdating] = useState(false);
  const [message, setMessage] = useState("");
  const analyticsCollectionUnavailable = analyticsPreference !== null && !analyticsPreference.collection_enabled;
  const analyticsSwitchDisabled = analyticsPreference === null
    || analyticsUpdating
    || (analyticsCollectionUnavailable && !analyticsPreference.enabled);

  useEffect(() => {
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.json())
      .then(setSession)
      .catch(() => setSession({ authenticated: false }));
    fetch("/api/backend/api/usage", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then(setUsage)
      .catch(() => setUsage(null));
    fetch("/api/backend/api/account/entitlements", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then(setEntitlements)
      .catch(() => setEntitlements(null));
    fetch("/api/backend/api/consents", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { items: [] }))
      .then((payload) => setConsents(payload.items ?? []))
      .catch(() => setConsents([]));
    fetch("/api/backend/api/account/privacy-preferences", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { items: [] }))
      .then((payload) => setAnalyticsPreference(payload.items?.[0] ?? null))
      .catch(() => setAnalyticsPreference(null));
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

  async function updateAnalyticsPreference(enabled: boolean) {
    if (enabled && analyticsPreference && !analyticsPreference.collection_enabled) {
      setMessage("Product analytics collection is unavailable for this deployment.");
      return;
    }
    setAnalyticsUpdating(true);
    setMessage("");
    const response = await fetch("/api/backend/api/account/privacy-preferences", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": `privacy-${crypto.randomUUID()}`
      },
      body: JSON.stringify({ purpose: "product_improvement", enabled })
    }).catch(() => null);
    const payload = await response?.json().catch(() => ({}));
    if (!response?.ok || !payload?.preference) {
      setMessage(payload?.detail ?? "Analytics preference could not be updated.");
      setAnalyticsUpdating(false);
      return;
    }
    setAnalyticsPreference(payload.preference);
    setMessage(
      !payload.preference.collection_enabled
        ? "Stored optional product analytics preference withdrawn and existing events removed. Collection is unavailable for this deployment."
        : enabled
          ? "Optional product analytics enabled."
          : "Optional product analytics disabled and existing events removed."
    );
    setAnalyticsUpdating(false);
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
        <h2>Product analytics</h2>
        <label className="privacy-switch" htmlFor="product-analytics-preference">
          <input
            aria-describedby="product-analytics-description product-analytics-status"
            checked={analyticsPreference?.enabled ?? false}
            disabled={analyticsSwitchDisabled}
            id="product-analytics-preference"
            onChange={(event) => void updateAnalyticsPreference(event.currentTarget.checked)}
            role="switch"
            type="checkbox"
          />
          <span>Share optional product events</span>
        </label>
        <p id="product-analytics-description">
          Helps improve core workflows using four bounded event types. Strategy text, emails,
          addresses, URLs, tokens, and resource identifiers are never included.
        </p>
        <p className="muted-small" id="product-analytics-status" role="status">
          {analyticsUpdating
            ? "Updating preference..."
            : analyticsCollectionUnavailable
              ? analyticsPreference?.enabled
                ? "Collection is unavailable for this deployment. You can withdraw the previously recorded preference."
                : "Collection is unavailable for this deployment."
              : analyticsPreference?.requires_reconsent
                ? "The privacy terms changed. Turn sharing on again to opt in to the current version."
                : analyticsPreference?.enabled
                  ? "Optional product analytics is enabled."
                  : "Collection is available and remains off until you opt in."}
        </p>
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
      <article className="panel">
        <h2>Entitlements</h2>
        {entitlements ? (
          <>
            <p>{entitlements.plan} {entitlements.version ? `v${entitlements.version}` : ""} ({entitlements.provenance})</p>
            <p>Admission quota and completed usage are separate records.</p>
            <ul className="compact-list">
              {Object.entries(entitlements.limits).map(([key, limit]) => (
                <li key={key}>{key}: {limit}</li>
              ))}
            </ul>
            <h3>Shadow comparison</h3>
            <ul className="compact-list">
              {entitlements.comparisons.map((comparison) => (
                <li key={comparison.key}>{comparison.key}: {comparison.result}</li>
              ))}
            </ul>
            <h3>Completed non-billable usage</h3>
            <ul className="compact-list">
              {Object.entries(entitlements.completed_usage).map(([unit, count]) => <li key={unit}>{unit}: {count}</li>)}
            </ul>
          </>
        ) : <p>Entitlement details are available after login.</p>}
      </article>
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
