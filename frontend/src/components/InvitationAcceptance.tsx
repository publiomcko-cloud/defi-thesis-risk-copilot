"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type AcceptanceResult = {
  organization_id: string;
  role: string;
};

export function InvitationAcceptance() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryToken = searchParams.get("token") ?? "";
  const [token, setToken] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "success" | "error" | "authentication_required">("idle");
  const [message, setMessage] = useState("");
  const [organizationId, setOrganizationId] = useState("");

  useEffect(() => {
    if (!queryToken) return;
    setToken(queryToken);
    router.replace(pathname, { scroll: false });
  }, [pathname, queryToken, router]);

  async function acceptInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submittedToken = token.trim();
    if (!submittedToken) {
      setState("error");
      setMessage("Enter an invitation token to continue.");
      return;
    }
    setState("loading");
    setMessage("");
    const response = await fetch("/api/backend/api/organization-invitations/accept", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: submittedToken })
    });
    const payload = await readJson<AcceptanceResult & { detail?: string }>(response);
    setToken("");
    router.replace(pathname, { scroll: false });
    if (!response.ok || !payload) {
      if (response.status === 401) {
        setState("authentication_required");
        setMessage("Log in with the invited email address before accepting this invitation.");
      } else if (response.status === 403) {
        setState("error");
        setMessage("This invitation belongs to a different authenticated email address.");
      } else {
        setState("error");
        setMessage("This invitation is expired, revoked, superseded, already accepted, or invalid.");
      }
      return;
    }
    setOrganizationId(payload.organization_id);
    setState("success");
    setMessage(`Invitation accepted. You joined the organization as ${payload.role}.`);
  }

  return (
    <section className="stack invitation-acceptance">
      <form className="form-panel auth-form" onSubmit={acceptInvitation}>
        <h2>Accept invitation</h2>
        <label htmlFor="organization-invitation-token">
          Invitation token
          <input
            autoComplete="off"
            id="organization-invitation-token"
            onChange={(event) => setToken(event.target.value)}
            required
            spellCheck={false}
            value={token}
          />
        </label>
        <button className="primary-action" disabled={state === "loading"} type="submit">
          {state === "loading" ? "Accepting..." : "Accept invitation"}
        </button>
      </form>
      {state === "authentication_required" ? (
        <section className="notice" role="status">
          <h2>Authentication required</h2>
          <p>{message}</p>
          <Link className="primary-link" href="/login">Log in</Link>
        </section>
      ) : null}
      {state === "error" ? <p className="error-text" role="alert">{message}</p> : null}
      {state === "success" ? (
        <section className="panel" role="status">
          <h2>Invitation accepted</h2>
          <p>{message}</p>
          <Link className="primary-link" href={`/organizations/${encodeURIComponent(organizationId)}`}>Open organization</Link>
        </section>
      ) : null}
    </section>
  );
}

async function readJson<T>(response: Response): Promise<T | null> {
  try {
    return await response.json() as T;
  } catch {
    return null;
  }
}
