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

const quickLinks = [
  { href: "/analyze", label: "Analyze" },
  { href: "/simulate", label: "Simulator" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/options", label: "Options" },
  { href: "/review", label: "Review queue" },
  { href: "/admin", label: "Admin" }
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
    try {
      const [nextStatus, nextScenarios] = await Promise.all([
        fetchDemoStatus(),
        fetchDemoScenarios()
      ]);
      setStatus(nextStatus);
      setScenarios(nextScenarios);
      try {
        setDeployment(await fetchDeploymentStatus());
      } catch {
        setDeployment(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo status failed");
    } finally {
      setLoading(false);
    }
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
    refreshDemo();
  }, [refreshDemo]);

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Final Phase 14</p>
        <h1>Portfolio Demo</h1>
        <p>
          Seed deterministic demo records, open example reports, and walk through
          discovery, RAG review, watchlist alerts, options analysis, and Vast.ai
          dry-run controls without paid APIs or wallet access.
        </p>
        <div className="action-row">
          <button
            className="primary-action"
            disabled={seeding}
            onClick={handleSeed}
            type="button"
          >
            {seeding ? "Seeding..." : "Seed demo data"}
          </button>
          <Link className="secondary-link" href="/reports/demo_report_pendle_pt_loop">
            Open main report
          </Link>
        </div>
      </section>

      {error ? <p className="error-text">{error}</p> : null}
      {message ? <p className="success-text">{message}</p> : null}

      {deployment?.public_demo_mode ? (
        <section className="notice">
          <h2>Public Synthetic Demo</h2>
          <p>
            This hosted mode is configured for portfolio review: LLM synthesis is
            disabled by default, Vast.ai is disabled or dry-run only, provider
            credential changes are blocked, and every demo record is synthetic.
          </p>
        </section>
      ) : null}

      <section className="panel">
        <h2>Seed Status</h2>
        <p>
          {loading
            ? "Checking demo data..."
            : status?.seeded
              ? "Demo data is available in the local database."
              : "Demo data has not been seeded yet."}
        </p>
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
        <h2>Demo Paths</h2>
        <div className="scenario-grid">
          {scenarios.map((scenario) => (
            <article className="scenario-card" key={scenario.id}>
              <p className="eyebrow">{scenario.tags.join(" / ")}</p>
              <h3>{scenario.title}</h3>
              <p>{scenario.summary}</p>
              <p>{scenario.safety_note}</p>
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
        </div>
      </section>

      <section className="panel">
        <h2>Quick Links</h2>
        <div className="action-row">
          {quickLinks.map((link) => (
            <Link className="secondary-link" href={link.href} key={link.href}>
              {link.label}
            </Link>
          ))}
        </div>
      </section>

      <section className="notice">
        <h2>Reproduce from a terminal</h2>
        <p>
          Run <code>backend/.venv/bin/python backend/scripts/seed_demo_data.py</code>{" "}
          or POST <code>/api/demo/seed</code>, then open <code>/demo</code> and
          the linked reports.
        </p>
      </section>

      <DisclaimerBox text="Demo records are synthetic and educational. They do not provide financial advice, connect wallets, sign transactions, execute trades, or rent real GPU infrastructure." />
    </main>
  );
}
