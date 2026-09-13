"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PublicAdminBoundary } from "@/components/PublicAdminBoundary";
import { fetchTrainingGovernance, sealTrainingManifest, submitLocalTrainingRun } from "@/lib/api";
import type { TrainingGovernance } from "@/lib/types";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function TrainingGovernancePage() {
  if (publicDemoMode) {
    return <PublicAdminBoundary title="Training governance is private" description="Local training evidence is available only to authenticated platform administrators." />;
  }
  return <PrivateTrainingGovernancePage />;
}

function PrivateTrainingGovernancePage() {
  const [snapshot, setSnapshot] = useState<TrainingGovernance | null>(null);
  const [activeAction, setActiveAction] = useState<"seal" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setError(null);
    try {
      setSnapshot(await fetchTrainingGovernance());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Training governance could not be loaded.");
    }
  }

  async function run(action: "seal" | "run") {
    setActiveAction(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "seal") {
        const manifest = await sealTrainingManifest();
        setMessage(`Manifest ${manifest.id} is sealed.`);
      } else {
        const trainingRun = await submitLocalTrainingRun(`training_${crypto.randomUUID()}`);
        setMessage(`Run ${trainingRun.id} is ${trainingRun.status}.`);
      }
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Training governance action failed.");
    } finally {
      setActiveAction(null);
    }
  }

  const profile = snapshot?.compute_profile;
  const recipe = snapshot?.recipe;
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Training Governance</h1>
        <p>Server-owned synthetic manifests and local-fake execution records.</p>
      </section>

      <div className="stack">
        <section className="panel">
          <div className="section-toolbar">
            <div><h2>Local Profile</h2></div>
            <Link className="secondary-link" href="/admin">Admin Home</Link>
          </div>
          <div className="meta-grid">
            <Metric label="Profile" value={text(profile?.compute_profile_id)} />
            <Metric label="Provider" value={text(profile?.provider)} />
            <Metric label="Network" value={text(profile?.network_policy)} />
            <Metric label="Concurrent" value={text(profile?.max_concurrency)} />
            <Metric label="Cost cap" value={text(profile?.max_total_cost_microusd)} />
            <Metric label="Recipe" value={text(recipe?.recipe_key)} />
          </div>
          <div className="action-row">
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void refresh()} type="button">Refresh</button>
            <button className="secondary-action" disabled={activeAction !== null} onClick={() => void run("seal")} type="button">
              {activeAction === "seal" ? "Sealing..." : "Seal Manifest"}
            </button>
            <button className="primary-action" disabled={activeAction !== null} onClick={() => void run("run")} type="button">
              {activeAction === "run" ? "Submitting..." : "Queue Local Evidence"}
            </button>
          </div>
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="panel">
          <h2>Sealed Manifests</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Manifest</th><th>Split</th><th>Checksum</th><th>Created</th></tr></thead>
              <tbody>
                {snapshot?.manifests.length ? snapshot.manifests.map((manifest) => (
                  <tr key={manifest.id}>
                    <td><strong>{manifest.dataset_version}</strong><span>{manifest.id}</span></td>
                    <td>{manifest.train_count} train / {manifest.validation_count} validation / {manifest.test_count} test</td>
                    <td className="mono">{manifest.manifest_checksum.slice(0, 16)}</td>
                    <td>{new Date(manifest.created_at).toLocaleString()}</td>
                  </tr>
                )) : <tr><td colSpan={4}>No sealed manifests.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <h2>Runs</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Run</th><th>State</th><th>Artifacts</th><th>Created</th></tr></thead>
              <tbody>
                {snapshot?.runs.length ? snapshot.runs.map((run) => (
                  <tr key={run.id}>
                    <td><strong>{run.id}</strong><span>{run.compute_profile_id}</span></td>
                    <td><strong>{run.status}</strong><span>{run.real_training_occurred ? "training recorded" : "local fake"}</span></td>
                    <td>{run.artifacts.length ? run.artifacts.map((artifact) => artifact.artifact_type).join(", ") : "None"}</td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                )) : <tr><td colSpan={4}>No training runs.</td></tr>}
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

function text(value: unknown): string {
  return value === undefined || value === null ? "-" : String(value);
}
