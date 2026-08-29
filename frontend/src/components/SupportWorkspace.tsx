"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

const REQUEST_TYPES = [
  { value: "support", label: "Support" },
  { value: "feedback", label: "Feedback" },
  { value: "abuse_report", label: "Abuse report" },
  { value: "privacy_access_export", label: "Privacy access/export" },
  { value: "privacy_deletion", label: "Privacy deletion" },
] as const;

type RequestType = (typeof REQUEST_TYPES)[number]["value"];
type CustomerRequest = {
  id: string;
  request_type: RequestType;
  subject: string;
  description: string;
  organization_id: string | null;
  workflow_state: "open" | "in_progress" | "resolved" | "closed";
  verification_state: "not_required" | "authenticated";
  created_at: string;
  updated_at: string;
  closed_at: string | null;
};
type Organization = { id: string; name: string; status: string };
type SessionPayload = { authenticated: boolean };

const privacyTypes = new Set<RequestType>(["privacy_access_export", "privacy_deletion"]);
const requestTypeLabels = Object.fromEntries(REQUEST_TYPES.map((item) => [item.value, item.label])) as Record<RequestType, string>;

export function SupportWorkspace() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [requests, setRequests] = useState<CustomerRequest[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [requestType, setRequestType] = useState<RequestType>("support");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [working, setWorking] = useState<"create" | "close" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [closeTarget, setCloseTarget] = useState<CustomerRequest | null>(null);
  const closeDialogRef = useRef<HTMLDialogElement>(null);

  const isPrivacyRequest = privacyTypes.has(requestType);
  const selectedRequest = useMemo(
    () => requests.find((item) => item.id === selectedId) ?? requests[0] ?? null,
    [requests, selectedId],
  );
  const organizationNameById = useMemo(
    () => new Map(organizations.map((organization) => [organization.id, organization.name])),
    [organizations],
  );

  useEffect(() => {
    if (closeTarget && closeDialogRef.current && !closeDialogRef.current.open) {
      closeDialogRef.current.showModal();
    }
  }, [closeTarget]);

  useEffect(() => {
    void loadWorkspace();
  }, []);

  async function loadWorkspace() {
    const sessionResponse = await fetch("/api/auth/session", { cache: "no-store" }).catch(() => null);
    const session = sessionResponse ? await readJson<SessionPayload>(sessionResponse) : null;
    if (!sessionResponse?.ok || !session?.authenticated) {
      setAuthenticated(false);
      return;
    }
    setAuthenticated(true);
    await refreshWorkspace();
  }

  async function refreshWorkspace() {
    const [requestsResponse, organizationsResponse] = await Promise.all([
      fetch("/api/backend/api/customer-requests", { cache: "no-store" }).catch(() => null),
      fetch("/api/backend/api/organizations", { cache: "no-store" }).catch(() => null),
    ]);
    if (!requestsResponse || requestsResponse.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!requestsResponse.ok) {
      setError(boundedError(requestsResponse, "load"));
      return;
    }
    const requestPayload = await readJson<{ items?: CustomerRequest[] }>(requestsResponse);
    const nextRequests = requestPayload?.items ?? [];
    setRequests(nextRequests);
    setSelectedId((current) => nextRequests.some((item) => item.id === current) ? current : nextRequests[0]?.id ?? "");
    const organizationPayload = organizationsResponse?.ok
      ? await readJson<{ items?: Organization[] }>(organizationsResponse)
      : null;
    setOrganizations((organizationPayload?.items ?? []).filter((organization) => organization.status === "active"));
  }

  function changeRequestType(nextType: RequestType) {
    setRequestType(nextType);
    if (privacyTypes.has(nextType)) {
      setOrganizationId("");
    }
  }

  async function createRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking("create");
    setMessage("");
    setError("");
    const payload = {
      request_type: requestType,
      subject,
      description,
      ...(!isPrivacyRequest && organizationId ? { organization_id: organizationId } : {}),
    };
    const response = await fetch("/api/backend/api/customer-requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => null);
    if (!response?.ok) {
      setError(response ? boundedError(response, "create") : "The request could not be sent. Try again.");
      setWorking(null);
      return;
    }
    const created = await readJson<CustomerRequest>(response);
    if (!created) {
      setError("The request could not be sent. Try again.");
      setWorking(null);
      return;
    }
    setRequests((current) => [created, ...current]);
    setSelectedId(created.id);
    setSubject("");
    setDescription("");
    setOrganizationId("");
    setMessage("Request created.");
    setWorking(null);
  }

  async function closeRequest() {
    if (!closeTarget) return;
    setWorking("close");
    setMessage("");
    setError("");
    const response = await fetch(`/api/backend/api/customer-requests/${encodeURIComponent(closeTarget.id)}/close`, {
      method: "POST",
    }).catch(() => null);
    if (!response?.ok) {
      setError(response ? boundedError(response, "close") : "The request could not be closed. Try again.");
      setWorking(null);
      return;
    }
    const closed = await readJson<CustomerRequest>(response);
    if (closed) {
      setRequests((current) => current.map((item) => item.id === closed.id ? closed : item));
      setSelectedId(closed.id);
      setMessage("Request closed.");
    }
    setCloseTarget(null);
    setWorking(null);
  }

  if (authenticated === null) {
    return <section className="panel loading-panel">Loading support workspace...</section>;
  }
  if (!authenticated) {
    return (
      <section className="panel">
        <h2>Sign in required</h2>
        <p>Support and privacy request records are private to your account.</p>
        <Link className="primary-link" href="/login">Log in</Link>
      </section>
    );
  }

  return (
    <div className="stack">
      <form className="form-panel" onSubmit={createRequest}>
        <div className="section-toolbar">
          <div>
            <h2>New request</h2>
            <p>Request text is private to your account. Attachments are not supported.</p>
          </div>
          <button className="secondary-action" disabled={working !== null} onClick={() => void refreshWorkspace()} type="button">Refresh</button>
        </div>
        <div className="support-form-grid">
          <label>
            Request type
            <select disabled={working !== null} onChange={(event) => changeRequestType(event.target.value as RequestType)} value={requestType}>
              {REQUEST_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
          </label>
          {!isPrivacyRequest ? (
            <label>
              Organization context <span className="muted-small">(optional)</span>
              <select disabled={working !== null} onChange={(event) => setOrganizationId(event.target.value)} value={organizationId}>
                <option value="">No organization context</option>
                {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
              </select>
            </label>
          ) : null}
        </div>
        <label>
          Subject
          <input aria-describedby="support-subject-count" disabled={working !== null} maxLength={120} onChange={(event) => setSubject(event.target.value)} required value={subject} />
          <span className="field-help" id="support-subject-count" role="status">{subject.length} / 120 characters</span>
        </label>
        <label>
          Description
          <textarea aria-describedby="support-description-count" disabled={working !== null} maxLength={4000} onChange={(event) => setDescription(event.target.value)} required rows={7} value={description} />
          <span className="field-help" id="support-description-count" role="status">{description.length} / 4,000 characters</span>
        </label>
        {requestType === "privacy_access_export" ? <p className="notice-copy">This creates a tracking record only. <Link className="text-link" href="/account">Open account export</Link> to use the existing export authority.</p> : null}
        {requestType === "privacy_deletion" ? <p className="notice-copy">This creates a tracking record only. <Link className="text-link" href="/account">Open account deletion</Link> to use the existing deletion authority and its confirmation checks.</p> : null}
        {error ? <p className="error-text" role="alert">{error}</p> : null}
        {message ? <p className="success-text" role="status">{message}</p> : null}
        <button className="primary-action" disabled={!subject || !description || working !== null} type="submit">{working === "create" ? "Creating..." : "Create request"}</button>
      </form>

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Your requests</h2>
            <p>Only requests returned for your account appear here.</p>
          </div>
        </div>
        {!requests.length ? <p>No requests yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Type</th><th>Subject</th><th>State</th><th>Verification</th><th>Organization</th><th>Created</th><th>Closed</th><th><span className="sr-only">View request</span></th></tr></thead>
              <tbody>
                {requests.map((item) => (
                  <tr key={item.id}>
                    <td>{requestTypeLabels[item.request_type]}</td>
                    <td>{item.subject}</td>
                    <td><span className={`request-state request-state-${item.workflow_state}`}>{item.workflow_state}</span></td>
                    <td>{item.verification_state === "authenticated" ? "Authenticated" : "Not required"}</td>
                    <td>{item.organization_id ? organizationNameById.get(item.organization_id) ?? "Organization context" : "None"}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td>{item.closed_at ? formatDate(item.closed_at) : "Open"}</td>
                    <td><button className="secondary-action" onClick={() => setSelectedId(item.id)} type="button">View</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedRequest ? (
        <section aria-labelledby="request-detail-heading" className="panel request-detail">
          <div className="section-toolbar">
            <div>
              <h2 id="request-detail-heading">Request detail</h2>
              <p>{requestTypeLabels[selectedRequest.request_type]} · {selectedRequest.workflow_state}</p>
            </div>
            {selectedRequest.workflow_state !== "closed" ? <button className="secondary-action" disabled={working !== null} onClick={() => setCloseTarget(selectedRequest)} type="button">Close request</button> : null}
          </div>
          <h3>{selectedRequest.subject}</h3>
          <p className="request-description">{selectedRequest.description}</p>
          <dl className="request-metadata">
            <div><dt>Verification</dt><dd>{selectedRequest.verification_state === "authenticated" ? "Authenticated" : "Not required"}</dd></div>
            <div><dt>Created</dt><dd>{formatDate(selectedRequest.created_at)}</dd></div>
            <div><dt>Updated</dt><dd>{formatDate(selectedRequest.updated_at)}</dd></div>
            <div><dt>Closed</dt><dd>{selectedRequest.closed_at ? formatDate(selectedRequest.closed_at) : "Not closed"}</dd></div>
          </dl>
        </section>
      ) : null}

      {closeTarget ? <dialog aria-labelledby="close-request-title" aria-modal="true" className="confirmation-dialog" onCancel={() => setCloseTarget(null)} ref={closeDialogRef}><h2 id="close-request-title">Close request</h2><p>Close “{closeTarget.subject}”? This requester action is final.</p><div className="action-row compact-actions"><button autoFocus className="secondary-action" disabled={working === "close"} onClick={() => setCloseTarget(null)} type="button">Cancel</button><button className="primary-action" disabled={working === "close"} onClick={() => void closeRequest()} type="button">{working === "close" ? "Closing..." : "Close request"}</button></div></dialog> : null}
    </div>
  );
}

function boundedError(response: Response, action: "load" | "create" | "close"): string {
  if (response.status === 401) return "Sign in to manage your requests.";
  if (response.status === 404) return "This request is unavailable.";
  if (response.status === 409 || response.status === 422) return "Review the request details and try again.";
  return action === "load" ? "Your requests could not be loaded. Try again." : `The request could not be ${action === "create" ? "created" : "closed"}. Try again.`;
}

async function readJson<T>(response: Response): Promise<T | null> {
  try {
    return await response.json() as T;
  } catch {
    return null;
  }
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}
