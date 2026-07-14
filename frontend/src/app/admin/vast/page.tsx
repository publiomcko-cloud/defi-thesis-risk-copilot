"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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

export default function VastAdminPage() {
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
    setActiveId("config");
    setMessage(null);
    setError(null);
    try {
      const nextConfig = await acknowledgeVastConfig("Admin reviewed Vast.ai runtime configuration.");
      setConfig(nextConfig);
      setMessage("Vast configuration review was recorded in the audit log.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Config review failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleStart() {
    setActiveId("start");
    setMessage(null);
    setError(null);
    try {
      const result = await startVastSession({
        model: config?.model || undefined,
        image: config?.image || undefined,
        allow_remote_gpu: false,
        warm_instance: false
      });
      setMessage(`Vast session ${result.session.id} reached ${result.session.status}.`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast session start failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleTestPrompt(sessionId: string) {
    setActiveId(`test:${sessionId}`);
    setMessage(null);
    setError(null);
    try {
      const prompt = promptBySession[sessionId] || "Reply with a short safe connectivity check.";
      const result = await testVastPrompt(sessionId, prompt);
      setMessage(`${result.provider} returned: ${result.output}`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast test prompt failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleDestroy(sessionId: string) {
    setActiveId(`destroy:${sessionId}`);
    setMessage(null);
    setError(null);
    try {
      const result = await destroyVastSession(sessionId);
      setMessage(`Session ${result.session.id} is ${result.session.status}.`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast destroy failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleCleanup() {
    setActiveId("cleanup");
    setMessage(null);
    setError(null);
    try {
      const result = await cleanupVastSessions();
      setMessage(`Cleanup destroyed ${result.cleaned_count} sessions and recorded ${result.failed_count} failures.`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Vast cleanup failed.");
    } finally {
      setActiveId(null);
    }
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Vast.ai</h1>
        <p>
          Manually warm up an optional ephemeral model session, run a safe test
          prompt, and destroy stale GPU sessions.
        </p>
      </section>

      <div className="stack">
        <section className="panel">
          <div className="section-toolbar">
            <div>
              <h2>Runtime Config</h2>
              <p>
                Vast.ai is disabled by default. Dry-run mode simulates the
                lifecycle without renting a real instance.
              </p>
            </div>
            <Link className="secondary-link" href="/admin">
              Admin Home
            </Link>
          </div>
          {config ? (
            <div className="meta-grid">
              <div>
                <span>Enabled</span>
                <strong>{config.enabled ? "true" : "false"}</strong>
              </div>
              <div>
                <span>Dry run</span>
                <strong>{config.dry_run ? "true" : "false"}</strong>
              </div>
              <div>
                <span>Max cost</span>
                <strong>${config.max_hourly_cost_usd}/hr</strong>
              </div>
              <div>
                <span>Max runtime</span>
                <strong>{config.max_session_minutes} min</strong>
              </div>
              <div>
                <span>Max active</span>
                <strong>{config.max_active_instances}</strong>
              </div>
              <div>
                <span>GPU allowlist</span>
                <strong>{config.gpu_allowlist.join(", ") || "none"}</strong>
              </div>
              <div>
                <span>Credential</span>
                <strong>{config.credential_name}</strong>
              </div>
              <div>
                <span>Env key</span>
                <strong>{config.has_env_api_key ? "configured" : "not configured"}</strong>
              </div>
            </div>
          ) : null}
          <div className="action-row">
            <button className="secondary-action" disabled={activeId !== null} onClick={refresh} type="button">
              Refresh
            </button>
            <button className="secondary-action" disabled={activeId !== null} onClick={handleAcknowledge} type="button">
              Record Review
            </button>
            <button className="primary-action" disabled={activeId !== null || !config?.enabled} onClick={handleStart} type="button">
              {activeId === "start" ? "Starting..." : "Start Dry-Run Session"}
            </button>
            <button className="secondary-action" disabled={activeId !== null} onClick={handleCleanup} type="button">
              {activeId === "cleanup" ? "Cleaning..." : "Run Cleanup"}
            </button>
          </div>
          {config && !config.enabled ? <p className="error">Vast.ai is disabled. Set VAST_ENABLED=true to test dry-run sessions.</p> : null}
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="panel">
          <h2>Sessions</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Lifecycle</th>
                  <th>Cost Guard</th>
                  <th>Test Prompt</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={5}>No Vast sessions recorded.</td>
                  </tr>
                ) : (
                  sessions.map((session) => (
                    <tr key={session.id}>
                      <td>
                        <strong>{session.id}</strong>
                        <span>{session.model}</span>
                        <span>{session.gpu_name ?? "no GPU selected"}</span>
                      </td>
                      <td>
                        <strong>{session.status}</strong>
                        <span>{session.health_status ?? "health pending"}</span>
                        <span>{session.last_error ?? "no error"}</span>
                      </td>
                      <td>
                        <strong>${session.hourly_cost_usd ?? 0}/hr</strong>
                        <span>{session.max_runtime_minutes} min max</span>
                      </td>
                      <td>
                        <textarea
                          aria-label={`Test prompt for ${session.id}`}
                          onChange={(event) =>
                            setPromptBySession((current) => ({
                              ...current,
                              [session.id]: event.target.value
                            }))
                          }
                          placeholder="Safe connectivity prompt"
                          rows={3}
                          value={promptBySession[session.id] ?? ""}
                        />
                      </td>
                      <td>
                        <div className="toolbar-actions">
                          <button
                            className="secondary-action"
                            disabled={activeId !== null || session.status !== "ready"}
                            onClick={() => handleTestPrompt(session.id)}
                            type="button"
                          >
                            {activeId === `test:${session.id}` ? "Testing..." : "Test"}
                          </button>
                          <button
                            className="secondary-action"
                            disabled={activeId !== null || session.status === "destroyed"}
                            onClick={() => handleDestroy(session.id)}
                            type="button"
                          >
                            {activeId === `destroy:${session.id}` ? "Destroying..." : "Destroy"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
