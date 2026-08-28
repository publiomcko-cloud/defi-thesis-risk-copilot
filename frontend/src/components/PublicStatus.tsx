"use client";

import { useEffect, useState } from "react";

type BackendStatus = "operational" | "unavailable" | "unknown";

export function PublicStatus() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("unknown");

  useEffect(() => {
    let active = true;
    fetch("/api/backend/health", { cache: "no-store" })
      .then((response) => {
        if (active) setBackendStatus(response.ok ? "operational" : "unavailable");
      })
      .catch(() => {
        if (active) setBackendStatus("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section aria-labelledby="service-status-heading" className="panel status-panel">
      <h2 id="service-status-heading">Current availability</h2>
      <p className="muted-small" role="status">
        {backendStatus === "unknown" ? "Checking the backend API." : "Current high-level service states."}
      </p>
      <ul className="status-list">
        <StatusItem label="Frontend" state="available" />
        <StatusItem label="Backend API" state={backendStatus} />
      </ul>
      <p className="field-help">
        This page reports only current, high-level availability. It does not provide service guarantees, incident history, or subscriber notifications.
      </p>
    </section>
  );
}

function StatusItem({ label, state }: { label: string; state: "available" | BackendStatus }) {
  const labelForState = state === "available" ? "Available" : state === "operational" ? "Operational" : state === "unavailable" ? "Unavailable" : "Unknown";
  return (
    <li className="status-row">
      <span>{label}</span>
      <strong className={`status-pill status-pill-${state}`}>{labelForState}</strong>
    </li>
  );
}
