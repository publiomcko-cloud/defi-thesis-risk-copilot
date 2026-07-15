"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DisclaimerBox } from "@/components/DisclaimerBox";
import {
  fetchDeploymentStatus,
  fetchDemoScenarios,
  fetchDemoStatus,
  seedDemoData
} from "@/lib/api";
import type { DemoScenario, DemoStatus, DeploymentStatus } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

const quickLinks = [
  { href: "/reports/demo_report_pendle_pt_loop", label: "Main risk report" },
  { href: "/analyze", label: "Strategy analysis" },
  { href: "/simulate", label: "Simulator" },
  { href: "/options", label: "Options" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/review", label: "Review workflow" }
];

export default function DemoPage() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [deployment, setDeployment] = useState<DeploymentStatus | null>(null);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const refreshDemo = useCallback(async () => {
    setLoading(true);
    setError("");

    const [statusResult, scenariosResult, deploymentResult] = await Promise.allSettled([
      fetchDemoStatus(),
      fetchDemoScenarios(),
      fetchDeploymentStatus()
    ]);

    if (statusResult.status === "fulfilled") {
      setStatus(statusResult.value);
    }
    if (scenariosResult.status === "fulfilled") {
      setScenarios(scenariosResult.value);
    }
    if (deploymentResult.status === "fulfilled") {
      setDeployment(deploymentResult.value);
    }

    if (statusResult.status === "rejected" && scenariosResult.status === "rejected") {
      setError(
        "The free-tier backend may be waking up. Open the backend readiness link or try again in a moment."
      );
    }
    setLoading(false);
  }, []);

  async function handleSeed() {
    setSeeding(true);
    setMessage("");
    setError("");
    try {
      const result = await seedDemoData();
      setMessage(result.message);
      await refreshDemo();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo seed failed");
    } finally {
      setSeeding(false);
    }
  }

  useEffect(() => {
    void refreshDemo();
  }, [refreshDemo]);

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Live portfolio demo</p>
        <h1>Explore the complete research workflow</h1>
        <p>
          Follow deterministic examples through strategy analysis, source review,
          watchlist alerts, options scenarios, and infrastructure controls without
          paid APIs, wallet access, or real GPU rental.
        </p>
        <div className="action-row">
          <Link className="primary-link" href="/reports/demo_report_pendle_pt_loop">
            Open Main Report
          </Link>
          <a
            className="secondary-link"
            href="https://defi-thesis-risk-copilot.onrender.com/ready"
            rel="noreferrer"
            target="_blank"
          >
            Check Backend Readiness
          </a>
          {!publicDemoMode && !status?.seeded ? (
            <button
              className="secondary-action"
              disabled={seeding}
              onClick={handleSeed}
              type="button"
            >
              {seeding ? "Seeding..." : "Seed local demo data"}
            </button>
          ) : null}
        </div>
      </section>

      {error ? (
        <section className="error-text" role="alert">
          <p>{error}</p>
          <button className="secondary-action" onClick={() => void refreshDemo()} type="button">
            Retry connection
          </button>
        </section>
      ) : null}
      {message ? <p className="success-text">{message}</p> : null}

      {publicDemoMode ? (
        <section className="notice">
          <h2>Public synthetic environment</h2>
          <p>
            This hosted deployment is read-only for discovery, review, RAG ingestion,
            watchlist changes, credentials, and infrastructure controls. Strategy,
            simulation, and options inputs are bounded and rate-limited.
          </p>
          <p>
            Do not submit private, confidential, wallet, or personally identifying
            information. This is a shared demonstration environment.
          </p>
        </section>
      ) : null}

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Environment status</h2>
            <p>
              {loading
                ? "Connecting to the free-tier backend. A cold start can take a moment..."
                : status?.seeded
                  ? "Deterministic demo records are ready in the hosted database."
                  : "Demo records are not available yet."}
            </p>
          </div>
          <button className="secondary-action" disabled={loading} onClick={() => void refreshDemo()} type="button">
            {loading ? "Checking..." : "Refresh"}
          </button>
        </div>
        {status ? (
          <div className="metric-grid">
            {Object.entries(status.counts).map(([key, value]) => (
              <div className="metric" key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        ) : null}
        {deployment ? (
          <div className="meta-grid">
            <div>
              <span>Environment</span>
              <strong>{deployment.app_environment}</strong>
            </div>
            <div>
              <span>Database</span>
              <strong>{deployment.database_connected ? "connected" : "unavailable"}</strong>
            </div>
            <div>
              <span>LLM synthesis</span>
              <strong>{deployment.llm_synthesis_enabled ? "enabled" : "disabled"}</strong>
            </div>
            <div>
              <span>Vast.ai</span>
              <strong>{deployment.vast_enabled ? "enabled" : "disabled"}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <h2>Guided demo paths</h2>
        <div className="scenario-grid">
          {scenarios.map((scenario, index) => (
            <article className="scenario-card" key={scenario.id}>
              <p className="eyebrow">Step {index + 1} · {scenario.tags.join(" / ")}</p>
              <h3>{scenario.title}</h3>
              <p>{scenario.summary}</p>
              <p className="muted-small">{scenario.safety_note}</p>
              <div className="action-row compact-actions">
                <Link className="secondary-link" href={scenario.primary_path}>
                  Open workflow
                </Link>
                {scenario.report_id ? (
                  <Link className="secondary-link" href={`/reports/${scenario.report_id}`}>
                    View report
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
          {!loading && scenarios.length === 0 ? (
            <p>No scenario metadata is currently available.</p>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <h2>Explore by capability</h2>
        <div className="action-row">
          {quickLinks.map((link) => (
            <Link className="secondary-link" href={link.href} key={link.href}>
              {link.label}
            </Link>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Inspect the implementation</h2>
        <p>
          Review the architecture, tests, deployment configuration, and consolidated
          development plan directly in the repository.
        </p>
        <div className="action-row compact-actions">
          <a
            className="secondary-link"
            href="https://github.com/publiomcko-cloud/defi-thesis-risk-copilot"
            rel="noreferrer"
            target="_blank"
          >
            Open GitHub
          </a>
          <a
            className="secondary-link"
            href="https://defi-thesis-risk-copilot.onrender.com/docs"
            rel="noreferrer"
            target="_blank"
          >
            Open API Docs
          </a>
        </div>
      </section>

      <DisclaimerBox text="Demo records are synthetic and educational. They do not provide financial advice, connect wallets, sign transactions, execute trades, or rent real GPU infrastructure." />
    </main>
  );
}
