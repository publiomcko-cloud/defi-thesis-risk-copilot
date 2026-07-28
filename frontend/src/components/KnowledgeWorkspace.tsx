"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import {
  createKnowledgeSource,
  deleteKnowledgeDocument,
  deleteKnowledgeSource,
  fetchCurrentUser,
  fetchKnowledgeReadiness,
  fetchKnowledgeSourceDocuments,
  fetchKnowledgeSources,
  rollbackKnowledgeDocument,
  submitKnowledgeEmbedding,
  submitKnowledgeIngestion,
  updateKnowledgeSourceTrust,
  uploadKnowledgeDocument,
  uploadKnowledgeDocumentVersion
} from "@/lib/api";
import type { KnowledgeDocument, KnowledgeReadiness, KnowledgeSource, KnowledgeVisibility } from "@/lib/types";

type OrganizationOption = { id: string; name: string };

function actionKey(prefix: string, id: string) {
  return `${prefix}-${id}-${Date.now()}`;
}

export function KnowledgeWorkspace() {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [organizations, setOrganizations] = useState<OrganizationOption[]>([]);
  const [readiness, setReadiness] = useState<KnowledgeReadiness | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [visibility, setVisibility] = useState<KnowledgeVisibility>("private");
  const [title, setTitle] = useState("");
  const [protocol, setProtocol] = useState("");
  const [sourceType, setSourceType] = useState("upload");
  const [organizationId, setOrganizationId] = useState("");
  const [sourceUri, setSourceUri] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedSource = useMemo(
    () => sources.find((source) => source.id === selectedSourceId) ?? null,
    [selectedSourceId, sources]
  );

  useEffect(() => {
    void refreshSources();
    void loadSessionContext();
  }, []);

  useEffect(() => {
    if (selectedSourceId) {
      void refreshDocuments(selectedSourceId);
    } else {
      setDocuments([]);
    }
  }, [selectedSourceId]);

  async function loadSessionContext() {
    try {
      const user = await fetchCurrentUser();
      setIsAdmin(user.role === "admin" || user.platform_role === "admin");
      if (user.role === "admin" || user.platform_role === "admin") {
        setReadiness(await fetchKnowledgeReadiness());
      }
    } catch {
      // The workspace remains useful to an authenticated source manager even
      // when admin-only operational readiness is intentionally unavailable.
      setReadiness(null);
    }
    try {
      const response = await fetch("/api/backend/api/organizations", { cache: "no-store" });
      if (response.ok) {
        setOrganizations((await response.json()).items);
      }
    } catch {
      setOrganizations([]);
    }
  }

  async function refreshSources() {
    try {
      setSources(await fetchKnowledgeSources());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Knowledge sources could not be loaded.");
    }
  }

  async function refreshDocuments(sourceId: string) {
    try {
      setDocuments(await fetchKnowledgeSourceDocuments(sourceId));
    } catch (caught) {
      setDocuments([]);
      setError(caught instanceof Error ? caught.message : "Knowledge documents could not be loaded.");
    }
  }

  async function createSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const source = await createKnowledgeSource({
        visibility,
        title,
        source_type: sourceType,
        organization_id: visibility === "organization" ? organizationId : undefined,
        source_uri: sourceUri || undefined,
        canonical_uri: sourceUri || undefined,
        protocol: protocol || undefined
      });
      setMessage("Knowledge source registered.");
      setTitle("");
      setProtocol("");
      setSourceUri("");
      setSelectedSourceId(source.id);
      await refreshSources();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Knowledge source could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadNewDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSourceId || !selectedFile) {
      setError("Select a source and a supported file first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await uploadKnowledgeDocument(selectedSourceId, selectedFile);
      setSelectedFile(null);
      setMessage("Document uploaded. Submit ingestion only after source approval and worker readiness.");
      await refreshDocuments(selectedSourceId);
      await refreshSources();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Knowledge document upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadVersion(documentId: string, event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !selectedSourceId) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await uploadKnowledgeDocumentVersion(documentId, file);
      setMessage("New immutable document version uploaded.");
      await refreshDocuments(selectedSourceId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Document version upload failed.");
    } finally {
      event.target.value = "";
      setBusy(false);
    }
  }

  async function runVersionAction(
    label: string,
    action: () => Promise<void>
  ) {
    setBusy(true);
    setError("");
    try {
      await action();
      setMessage(label);
      if (selectedSourceId) {
        await refreshDocuments(selectedSourceId);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Knowledge operation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function removeSource(sourceId: string) {
    if (!window.confirm("Delete this source and queue its durable versions for retention cleanup?")) {
      return;
    }
    await runVersionAction("Knowledge source deleted.", async () => {
      await deleteKnowledgeSource(sourceId);
      if (selectedSourceId === sourceId) {
        setSelectedSourceId("");
      }
      await refreshSources();
    });
  }

  async function changeTrustState(trustState: string) {
    if (!selectedSource) {
      return;
    }
    await runVersionAction("Knowledge source trust state updated.", async () => {
      await updateKnowledgeSourceTrust(selectedSource.id, trustState);
      await refreshSources();
    });
  }

  async function removeDocument(documentId: string) {
    if (!window.confirm("Delete this document and queue its durable versions for retention cleanup?")) {
      return;
    }
    await runVersionAction("Knowledge document deleted.", () => deleteKnowledgeDocument(documentId));
  }

  return (
    <div className="stack">
      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Knowledge Sources</h2>
            <p>Private and organization documents stay scoped to the authenticated source owner or active organization membership.</p>
          </div>
          <button className="secondary-action" disabled={busy} onClick={() => void refreshSources()} type="button">Refresh</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Source</th><th>Scope</th><th>Trust</th><th>Status</th><th /></tr></thead>
            <tbody>
              {sources.length ? sources.map((source) => (
                <tr key={source.id}>
                  <td><strong>{source.title}</strong><span>{source.protocol ?? source.source_type}</span></td>
                  <td>{source.visibility}{source.organization_id ? " organization" : ""}</td>
                  <td><span className={`status-badge status-${source.trust_state}`}>{source.trust_state.replaceAll("_", " ")}</span></td>
                  <td>{source.status}</td>
                  <td className="table-actions">
                    <button className="secondary-action" onClick={() => setSelectedSourceId(source.id)} type="button">Open</button>
                    <button className="secondary-action" disabled={busy} onClick={() => void removeSource(source.id)} type="button">Delete</button>
                  </td>
                </tr>
              )) : <tr><td colSpan={5}>No visible knowledge sources.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <form className="form-panel auth-form" onSubmit={createSource}>
        <h2>Register Source</h2>
        <div className="form-grid">
          <label>Title<input onChange={(event) => setTitle(event.target.value)} required value={title} /></label>
          <label>Protocol<input onChange={(event) => setProtocol(event.target.value)} placeholder="aave" value={protocol} /></label>
          <label>Source type<input onChange={(event) => setSourceType(event.target.value)} required value={sourceType} /></label>
          <label>Reference URL or label<input onChange={(event) => setSourceUri(event.target.value)} value={sourceUri} /></label>
          <label>Visibility
            <select onChange={(event) => setVisibility(event.target.value as KnowledgeVisibility)} value={visibility}>
              <option value="private">Private</option>
              <option value="organization">Organization</option>
              {isAdmin ? <option value="public">Public</option> : null}
            </select>
          </label>
          {visibility === "organization" ? (
            <label>Organization
              <select onChange={(event) => setOrganizationId(event.target.value)} required value={organizationId}>
                <option value="">Select organization</option>
                {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
              </select>
            </label>
          ) : null}
        </div>
        <button className="primary-action" disabled={busy} type="submit">Register source</button>
      </form>

      {selectedSource ? (
        <section className="panel">
          <div className="section-toolbar">
            <div><h2>{selectedSource.title}</h2><p>{selectedSource.visibility} source · {selectedSource.trust_state.replaceAll("_", " ")}</p></div>
            <div className="toolbar-actions">
              <label className="trust-control">Trust state
                <select disabled={busy} onChange={(event) => void changeTrustState(event.target.value)} value={selectedSource.trust_state}>
                  <option value="needs_review">Needs review</option>
                  <option value="approved_for_rag">Approved for RAG</option>
                  <option value="rejected">Rejected</option>
                  <option value="archived">Archived</option>
                </select>
              </label>
              <button className="secondary-action" onClick={() => setSelectedSourceId("")} type="button">Close</button>
            </div>
          </div>
          <form className="upload-row" onSubmit={uploadNewDocument}>
            <label>Upload document<input accept=".txt,.md,.markdown,.htm,.html,.pdf,text/plain,text/markdown,text/html,application/pdf" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} type="file" /></label>
            <button className="primary-action" disabled={busy || !selectedFile} type="submit">Upload document</button>
          </form>
          <div className="knowledge-document-list">
            {documents.length ? documents.map((document) => (
              <article className="knowledge-document" key={document.id}>
                <div className="section-toolbar">
                  <div><h3>{document.filename}</h3><p>{document.media_type} · {document.status}</p></div>
                  <div className="toolbar-actions">
                    <label className="file-action">New version<input accept=".txt,.md,.markdown,.htm,.html,.pdf,text/plain,text/markdown,text/html,application/pdf" disabled={busy} onChange={(event) => void uploadVersion(document.id, event)} type="file" /></label>
                    <button className="secondary-action" disabled={busy} onClick={() => void removeDocument(document.id)} type="button">Delete document</button>
                  </div>
                </div>
                <div className="table-wrap"><table><thead><tr><th>Version</th><th>Status</th><th>Lineage</th><th /></tr></thead><tbody>
                  {document.versions.map((version) => (
                    <tr key={version.id}>
                      <td>v{version.version_number}{document.current_version_id === version.id ? " current" : ""}</td>
                      <td>{version.status}</td>
                      <td><span>{version.parser_version ?? "Not ingested"}</span><span>{version.embedding_model ?? "No active embeddings"}</span></td>
                      <td className="table-actions">
                        <button className="secondary-action" disabled={busy} onClick={() => void runVersionAction("Document ingestion submitted.", () => submitKnowledgeIngestion(version.id, actionKey("ingest", version.id)))} type="button">Ingest</button>
                        <button className="secondary-action" disabled={busy} onClick={() => void runVersionAction("Document embedding submitted.", () => submitKnowledgeEmbedding(version.id, actionKey("embed", version.id)))} type="button">Embed</button>
                        {document.current_version_id !== version.id && ["ready", "superseded"].includes(version.status) ? <button className="secondary-action" disabled={busy} onClick={() => void runVersionAction("Document version restored.", async () => { await rollbackKnowledgeDocument(document.id, version.id); })} type="button">Restore</button> : null}
                      </td>
                    </tr>
                  ))}
                </tbody></table></div>
              </article>
            )) : <p className="muted-small">No documents have been uploaded for this source.</p>}
          </div>
        </section>
      ) : null}

      {isAdmin && readiness ? <KnowledgeReadinessPanel readiness={readiness} /> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {message ? <p className="form-success">{message}</p> : null}
    </div>
  );
}

function KnowledgeReadinessPanel({ readiness }: { readiness: KnowledgeReadiness }) {
  const flags = [
    ["Database", readiness.database_ready],
    ["pgvector", readiness.pgvector_ready],
    ["JSON fallback", readiness.json_fallback_ready],
    ["Private storage", readiness.storage_enabled],
    ["Ingestion jobs", readiness.document_ingest_enabled],
    ["Embeddings", readiness.embeddings_enabled],
    ["Shadow retrieval", readiness.shadow_retrieval_enabled],
    ["Public durable path", readiness.pgvector_primary_enabled]
  ];
  return (
    <section className="panel">
      <h2>Knowledge Readiness</h2>
      <div className="readiness-grid">
        {flags.map(([label, enabled]) => <div key={String(label)}><span>{label}</span><strong>{enabled ? "Ready" : "Disabled"}</strong></div>)}
        <div><span>Visible sources</span><strong>{readiness.visible_source_count}</strong></div>
        <div><span>Ready documents</span><strong>{readiness.ready_document_count}</strong></div>
        <div><span>Ready versions</span><strong>{readiness.ready_version_count}</strong></div>
        <div><span>Active embeddings</span><strong>{readiness.active_embedding_count}</strong></div>
        <div><span>Cleanup tasks</span><strong>{readiness.pending_cleanup_count}</strong></div>
      </div>
    </section>
  );
}
