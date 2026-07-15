"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PublicAdminBoundary } from "@/components/PublicAdminBoundary";
import {
  acknowledgeVastConfig,
  cleanupVastSessions,
  destroyVastSession,
  fetchVastConfig,
  fetchVastSessions,
  startVastSession,
  testVastPrompt
} from "@/lib/api";
import type { VastConfig, VastSession } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function VastAdminPage() {
  if (publicDemoMode) {
    return (
      <PublicAdminBoundary
        title="Vast.ai controls are private"
        description="GPU rental, model-session lifecycle, test prompts, cleanup, and cost controls require an authenticated private deployment."
      />
    );
  }

  return <PrivateVastAdminPage />;
}

function PrivateVastAdminPage() {
  const [config, setConfig] = useState<VastConfig | null>(null);
  const [sessions, setSessions] = useState<VastSession[]>([]);
  const [promptBySession, setPromptBySession] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setError(null);
    try {
      const [nextConfig, nextSessions] = await Promise.all([
        fetchVastConfig(),
        fetchVastSessions()
      ]);
      setConfig(nextConfig);
      setSessions(nextSessions.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast data failed to load.");
    }
  }

  async function handleAcknowledge() {
    await runAction("config", async () => {
      setConfig(await acknowledgeVastConfig("Admin reviewed Vast.ai runtime configuration."));
      setMessage("Vast configuration review was recorded in the audit log.");
    });
  }

  async function handleStart() {
    await runAction("start", async () => {
      const result = await startVastSession({
        model: config?.model || undefined,
        image: config?.image || undefined,
        allow_remote_gpu: false,
        warm_instance: false
      });
      setMessage(`Vast session ${result.session.id} reached ${result.session.status}.`);
      await refresh();
    });
  }

  async function handleTestPrompt(sessionId: string) {
    await runAction(`test:${sessionId}`, async () => {
      const prompt = promptBySession[sessionId] || "Reply with a short safe connectivity check.";
      const result = await testVastPrompt(sessionId, prompt);
      setMessage(`${result.provider} returned: ${result.output}`);
      await refresh();
    });
  }

  async function handleDestroy(sessionId: string) {
    await runAction(`destroy:${sessionId}`, async () => {
      const result = await destroyVastSession(sessionId);
      setMessage(`Session ${result.session.id} is ${result.session.status}.`);
      await refresh();
    });
  }

  async function handleCleanup() {
    await runAction("cleanup", async () => {
      const result = await cleanupVastSessions();
      setMessage(`Cleanup destroyed ${result.cleaned_count} sessions and recorded ${result.failed_count} failures.`);
      await refresh();
    });
  }

  async function runAction(id: string, action: () => Promise<void>) {
    setActiveId(id);
    setMessage(null);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast operation failed.");
    } finally {
      setActiveId(null);
    }
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Vast.ai</h1>
        <p>Warm an optional model session, test connectivity, and destroy or clean up GPU sessions.</p>
      </section>

      <div className="stack">
        <section className="panel">
          <div className="section-toolbar">
            <div>
              <h2>Runtime Configuration</h2>
              <p>Vast.ai remains disabled and dry-run by default.</p>
            </div>
            <Link className="secondary-link" href="/admin">Admin Home</Link>
          </div>
          {config ? (
            <div className="meta-grid">
              <Metric label="Enabled" value={config.enabled ? "true" : "false"} />
              <Metric label="Dry run" value={config.dry_run ? "true" : "false"} />
              <Metric label="Max cost" value={`$${config.max_hourly_cost_usd}/hr`} />
              <Metric label="Max runtime" value={`${config.max_session_minutes} min`} />
              <Metric label="Max active" value={String(config.max_active_instances)} />
              <Metric label="GPU allowlist" value={config.gpu_allowlist.join(", ") || "none"} />
              <Metric label="Credential" value={config.credential_name} />
              <Metric label="Environment key" value={config.has_env_api_key ? "configured" : "not configured"} />
            </div>
          ) : null}
          <div className="action-row">
            <button className="secondary-action" disabled={activeId !== null} onClick={refresh} type="button">Refresh</button>
            <button className="secondary-action" disabled={activeId !== null} onClick={handleAcknowledge} type="button">Record Review</button>
            <button className="primary-action" disabled={activeId !== null || !config?.enabled} onClick={handleStart} type="button">
              {activeId === "start" ? "Starting..." : "Start Dry-Run Session"}
            </button>
            <button className="secondary-action" disabled={activeId !== null} onClick={handleCleanup} type="button">
              {activeId === "cleanup" ? "Cleaning..." : "Run Cleanup"}
            </button>
          </div>
          {config && !config.enabled ? <p className="error">Vast.ai is disabled. Enable it only in a controlled private environment.</p> : null}
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="panel">
          <h2>Sessions</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Session</th><th>Lifecycle</th><th>Cost Guard</th><th>Test Prompt</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr><td colSpan={5}>No Vast sessions recorded.</td></tr>
                ) : sessions.map((session) => (
                  <tr key={session.id}>
                    <td><strong>{session.id}</strong><span>{session.model}</span><span>{session.gpu_name ?? "no GPU selected"}</span></td>
                    <td><strong>{session.status}</strong><span>{session.health_status ?? "health pending"}</span><span>{session.last_error ?? "no error"}</span></td>
                    <td><strong>${session.hourly_cost_usd ?? 0}/hr</strong><span>{session.max_runtime_minutes} min max</span></td>
                    <td>
                      <textarea
                        aria-label={`Test prompt for ${session.id}`}
                        onChange={(event) => setPromptBySession((current) => ({ ...current, [session.id]: event.target.value }))}
                        placeholder="Safe connectivity prompt"
                        rows={3}
                        value={promptBySession[session.id] ?? ""}
                      />
                    </td>
                    <td>
                      <div className="toolbar-actions">
                        <button className="secondary-action" disabled={activeId !== null || session.status !== "ready"} onClick={() => handleTestPrompt(session.id)} type="button">
                          {activeId === `test:${session.id}` ? "Testing..." : "Test"}
                        </button>
                        <button className="secondary-action" disabled={activeId !== null || session.status === "destroyed"} onClick={() => handleDestroy(session.id)} type="button">
                          {activeId === `destroy:${session.id}` ? "Destroying..." : "Destroy"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
