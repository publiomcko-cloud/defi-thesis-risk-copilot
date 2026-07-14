"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  createProviderCredential,
  fetchProviderCredentials,
  updateProviderCredential
} from "@/lib/api";
import type {
  ProviderCredentialMetadata,
  ProviderCredentialUpdateRequest,
  ProviderName
} from "@/lib/types";

const providerOptions: ProviderName[] = [
  "openai_compatible",
  "coingecko",
  "defillama_pro",
  "vast_ai"
];

export default function ProviderCredentialsPage() {
  const [items, setItems] = useState<ProviderCredentialMetadata[]>([]);
  const [provider, setProvider] = useState<ProviderName>("openai_compatible");
  const [name, setName] = useState("");
  const [secret, setSecret] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setError(null);
    try {
      const response = await fetchProviderCredentials();
      setItems(response.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Credential data failed to load.");
    }
  }

  async function handleCreate() {
    setActiveId("create");
    setMessage(null);
    setError(null);
    try {
      await createProviderCredential({ provider, name, secret, enabled });
      setName("");
      setSecret("");
      setEnabled(true);
      setMessage("Provider credential saved. Secret value is stored server-side and not returned.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Credential save failed.");
    } finally {
      setActiveId(null);
    }
  }

  async function handleToggle(item: ProviderCredentialMetadata) {
    await patchCredential(item.id, { enabled: !item.enabled });
  }

  async function handleRotate(item: ProviderCredentialMetadata) {
    const nextSecret = window.prompt(`Enter a new secret for ${item.name}`);
    if (!nextSecret) {
      return;
    }
    await patchCredential(item.id, { secret: nextSecret });
  }

  async function patchCredential(
    credentialId: string,
    payload: ProviderCredentialUpdateRequest
  ) {
    setActiveId(credentialId);
    setMessage(null);
    setError(null);
    try {
      await updateProviderCredential(credentialId, payload);
      setMessage("Provider credential updated.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Credential update failed.");
    } finally {
      setActiveId(null);
    }
  }

  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Admin</p>
        <h1>Provider Credentials</h1>
        <p>
          Store provider secrets on the backend and expose only safe metadata to
          the browser.
        </p>
      </section>

      <div className="stack">
        <section className="panel">
          <div className="section-toolbar">
            <div>
              <h2>Add Credential</h2>
              <p>Secrets are write-only from the UI after submission.</p>
            </div>
            <Link className="secondary-link" href="/admin">
              Admin Home
            </Link>
          </div>
          <div className="manual-grid">
            <label>
              Provider
              <select
                onChange={(event) => setProvider(event.target.value as ProviderName)}
                value={provider}
              >
                {providerOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Name
              <input
                onChange={(event) => setName(event.target.value)}
                placeholder="Local OpenAI-compatible gateway"
                value={name}
              />
            </label>
            <label>
              Secret
              <input
                autoComplete="off"
                onChange={(event) => setSecret(event.target.value)}
                type="password"
                value={secret}
              />
            </label>
            <label className="checkbox-label">
              <input
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
                type="checkbox"
              />
              Enabled
            </label>
          </div>
          <button
            className="primary-action"
            disabled={activeId !== null || !name.trim() || !secret.trim()}
            onClick={handleCreate}
            type="button"
          >
            {activeId === "create" ? "Saving..." : "Save Credential"}
          </button>
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="panel">
          <h2>Saved Credentials</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Credential</th>
                  <th>Secret</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={5}>No provider credentials stored.</td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.name}</strong>
                        <span>{item.provider}</span>
                      </td>
                      <td>ending {item.secret_last4}</td>
                      <td>{item.enabled ? "enabled" : "disabled"}</td>
                      <td>{new Date(item.updated_at).toLocaleString()}</td>
                      <td>
                        <div className="toolbar-actions">
                          <button
                            className="secondary-action"
                            disabled={activeId !== null}
                            onClick={() => handleToggle(item)}
                            type="button"
                          >
                            {item.enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            className="secondary-action"
                            disabled={activeId !== null}
                            onClick={() => handleRotate(item)}
                            type="button"
                          >
                            Rotate
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
