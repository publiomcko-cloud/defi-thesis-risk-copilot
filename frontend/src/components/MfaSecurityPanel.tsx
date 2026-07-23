"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import type { MfaEnrollment, MfaFactor, MfaState } from "@/lib/mfa-provider";

type RequestState = "idle" | "loading";

export function MfaSecurityPanel({ adminMfaRequired }: { adminMfaRequired: boolean }) {
  const [mfa, setMfa] = useState<MfaState | null>(null);
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [friendlyName, setFriendlyName] = useState("Authenticator app");
  const [selectedFactorId, setSelectedFactorId] = useState("");
  const [code, setCode] = useState("");
  const [requestState, setRequestState] = useState<RequestState>("idle");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [authRequired, setAuthRequired] = useState(false);

  const loadState = useCallback(async () => {
    setError("");
    const response = await fetch("/api/auth/mfa", { cache: "no-store" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setAuthRequired(response.status === 401);
      setError(body.detail ?? "MFA status could not be loaded.");
      return;
    }
    const nextState = body as MfaState;
    setMfa(nextState);
    setAuthRequired(false);
    setSelectedFactorId((current) => current || preferredFactor(nextState.factors)?.id || "");
  }, []);

  useEffect(() => {
    loadState().catch(() => setError("MFA status could not be loaded."));
  }, [loadState]);

  async function startEnrollment() {
    setRequestState("loading");
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/auth/mfa/enroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ friendly_name: friendlyName })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(body.detail ?? "MFA enrollment could not be started.");
        return;
      }
      const nextEnrollment = body as MfaEnrollment;
      setEnrollment(nextEnrollment);
      setSelectedFactorId(nextEnrollment.factor_id);
      setMessage("Scan the QR code, then enter the current code from your authenticator app.");
      await loadState();
    } catch {
      setError("MFA enrollment could not be started.");
    } finally {
      setRequestState("idle");
    }
  }

  async function verifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRequestState("loading");
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/auth/mfa/challenge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ factor_id: selectedFactorId, code })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(body.detail ?? "The verification code could not be confirmed.");
        return;
      }
      setCode("");
      setEnrollment(null);
      setMessage("MFA verified. This session now has AAL2 assurance.");
      await loadState();
    } catch {
      setError("The verification code could not be confirmed.");
    } finally {
      setRequestState("idle");
    }
  }

  async function removeFactor(factor: MfaFactor) {
    const confirmed = window.confirm(`Remove ${factor.friendly_name} from this account?`);
    if (!confirmed) {
      return;
    }
    setRequestState("loading");
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/auth/mfa/${encodeURIComponent(factor.id)}`, { method: "DELETE" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(body.detail ?? "The MFA factor could not be removed.");
        return;
      }
      setEnrollment(null);
      setSelectedFactorId("");
      setMessage("Authenticator removed.");
      await loadState();
    } catch {
      setError("The MFA factor could not be removed.");
    } finally {
      setRequestState("idle");
    }
  }

  if (authRequired) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Log in before managing authenticator factors.</p>
        <a className="primary-link" href="/login">Log in</a>
      </section>
    );
  }

  return (
    <section className="stack" aria-busy={requestState === "loading"}>
      <article className="panel">
        <div className="section-toolbar">
          <div>
            <h2>MFA status</h2>
            <p>
              {mfa?.current_level === "aal2"
                ? "This session has completed multi-factor verification."
                : "This session has password-level assurance and can be upgraded with an authenticator code."}
            </p>
          </div>
          <span className={`status-badge status-${mfa?.current_level === "aal2" ? "info" : "warning"}`}>
            {mfa?.current_level?.toUpperCase() ?? "Loading"}
          </span>
        </div>
        <p className="muted-small">
          {adminMfaRequired
            ? "Platform administrators must reach AAL2 before using administrator routes."
            : "MFA is optional for ordinary users and can be required for platform administrators."}
        </p>
      </article>

      {error ? <p className="error-text" role="alert">{error}</p> : null}
      {message ? <p className="success-text" role="status">{message}</p> : null}

      <article className="panel">
        <h2>Authenticator factors</h2>
        {mfa?.factors.length ? (
          <ul className="mfa-factor-list">
            {mfa.factors.map((factor) => (
              <li key={factor.id}>
                <div>
                  <strong>{factor.friendly_name}</strong>
                  <span>{factor.factor_type.toUpperCase()} · {factor.status}</span>
                </div>
                <button
                  className="secondary-action"
                  disabled={requestState === "loading"}
                  onClick={() => removeFactor(factor)}
                  type="button"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>No authenticator factor is enrolled.</p>
        )}
      </article>

      {enrollment ? (
        <article className="form-panel mfa-enrollment">
          <h2>Scan authenticator code</h2>
          <p>Add this account in your authenticator app. The setup secret is kept only in this page state.</p>
          {/* Supabase returns the TOTP QR as an SVG data image. */}
          <img alt="TOTP enrollment QR code" className="mfa-qr-code" src={enrollment.qr_code} />
          <div className="mfa-secret">
            <span>Manual setup secret</span>
            <code>{enrollment.secret}</code>
          </div>
        </article>
      ) : (
        <article className="form-panel">
          <h2>Add authenticator</h2>
          <label htmlFor="mfa-friendly-name">
            Authenticator name
            <input
              autoComplete="off"
              id="mfa-friendly-name"
              maxLength={64}
              onChange={(event) => setFriendlyName(event.target.value)}
              value={friendlyName}
            />
          </label>
          <button
            className="primary-action"
            disabled={requestState === "loading" || !mfa}
            onClick={startEnrollment}
            type="button"
          >
            Add authenticator
          </button>
        </article>
      )}

      {mfa?.factors.length || enrollment ? (
        <form className="form-panel" onSubmit={verifyCode}>
          <h2>Verify this session</h2>
          <label htmlFor="mfa-factor">
            Authenticator
            <select
              id="mfa-factor"
              onChange={(event) => setSelectedFactorId(event.target.value)}
              required
              value={selectedFactorId}
            >
              <option value="">Select an authenticator</option>
              {enrollment && !mfa?.factors.some((factor) => factor.id === enrollment.factor_id) ? (
                <option value={enrollment.factor_id}>{enrollment.friendly_name} (new)</option>
              ) : null}
              {mfa?.factors.map((factor) => (
                <option key={factor.id} value={factor.id}>{factor.friendly_name} ({factor.status})</option>
              ))}
            </select>
          </label>
          <label htmlFor="mfa-code">
            Verification code
            <input
              autoComplete="one-time-code"
              id="mfa-code"
              inputMode="numeric"
              maxLength={8}
              minLength={6}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
              pattern="[0-9]{6,8}"
              required
              value={code}
            />
          </label>
          <button
            className="primary-action"
            disabled={requestState === "loading" || !selectedFactorId}
            type="submit"
          >
            Verify code
          </button>
        </form>
      ) : null}
    </section>
  );
}

function preferredFactor(factors: MfaFactor[]): MfaFactor | undefined {
  return factors.find((factor) => factor.status === "verified") ?? factors[0];
}
