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

  useEffect(() => {
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.json())
      .then(setSession)
      .catch(() => setSession({ authenticated: false }));
  }, []);

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
      </article>
      <article className="panel">
        <h2>Security</h2>
        <p>MFA is optional for ordinary users and can be required for platform administrators.</p>
        <Link className="secondary-link" href="/account/security">Open security</Link>
      </article>
    </section>
  );
}
