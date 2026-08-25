"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Organization = { id: string; name: string; slug: string; status: string };
type Member = { id: string; user_id: string; email: string; role: string; status: string };
type Invitation = { id: string; destination_email: string; role: string; status: string; expires_at: string };
type SeatProjection = { limit: number; active: number; reserved: number; consumed: number; remaining: number };
type KnowledgeSource = { id: string; title: string; protocol: string; source_url: string; approval_status: string; storage_status: string };
type OneTimeInvitation = { invitationId: string; destinationEmail: string; token: string; action: "created" | "resent" };
type Confirmation = { kind: "delete" } | { kind: "transfer"; target: Member };
type SessionPayload = { authenticated: boolean; user?: { email?: string } };

const roleOptions = ["admin", "member", "viewer"] as const;

export function OrganizationManager({ initialOrganizationId }: { initialOrganizationId?: string }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [seats, setSeats] = useState<SeatProjection | null>(null);
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [currentUserEmail, setCurrentUserEmail] = useState("");
  const [newOrganizationName, setNewOrganizationName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<(typeof roleOptions)[number]>("member");
  const [transferTargetId, setTransferTargetId] = useState("");
  const [oneTimeInvitation, setOneTimeInvitation] = useState<OneTimeInvitation | null>(null);
  const [copyMessage, setCopyMessage] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [working, setWorking] = useState(false);
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceProtocol, setSourceProtocol] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [approvalConfirmed, setApprovalConfirmed] = useState(false);
  const confirmationDialogRef = useRef<HTMLDialogElement>(null);

  const selectedOrganization = organization ?? organizations.find((item) => item.id === selectedId) ?? null;
  const currentMembership = members.find(
    (member) => member.email.toLowerCase() === currentUserEmail.toLowerCase() && member.status === "active"
  );
  const isActive = selectedOrganization?.status === "active";
  const isOwner = currentMembership?.role === "owner";
  const isManager = currentMembership?.role === "owner" || currentMembership?.role === "admin";
  const canManage = Boolean(isActive && isManager);
  const canExport = Boolean((isActive && isManager) || (!isActive && isOwner));
  const activeMembers = members.filter((member) => member.status === "active");
  const transferTargets = useMemo(
    () => members.filter((member) => member.status === "active" && member.id !== currentMembership?.id),
    [currentMembership?.id, members]
  );

  useEffect(() => {
    void loadSession();
    void refreshOrganizations();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setOrganization(null);
      setMembers([]);
      setInvitations([]);
      setSeats(null);
      setKnowledgeSources([]);
      return;
    }
    setOneTimeInvitation(null);
    void refreshOrganizationData(selectedId);
  }, [selectedId, currentUserEmail]);

  useEffect(() => {
    if (!transferTargets.some((member) => member.id === transferTargetId)) {
      setTransferTargetId(transferTargets[0]?.id ?? "");
    }
  }, [transferTargetId, transferTargets]);

  useEffect(() => {
    if (confirmation && confirmationDialogRef.current && !confirmationDialogRef.current.open) {
      confirmationDialogRef.current.showModal();
    }
  }, [confirmation]);

  async function loadSession() {
    const response = await fetch("/api/auth/session", { cache: "no-store" });
    const payload = await readJson<SessionPayload>(response);
    setCurrentUserEmail(response.ok && payload?.authenticated ? payload.user?.email ?? "" : "");
  }

  async function refreshOrganizations() {
    const response = await fetch("/api/backend/api/organizations", { cache: "no-store" });
    const payload = await readJson<{ items: Organization[] }>(response);
    if (!response.ok || !payload) {
      setOrganizations([]);
      return;
    }
    setOrganizations(payload.items);
    setSelectedId((current) => (
      current
      || payload.items.find((item) => item.id === initialOrganizationId)?.id
      || payload.items[0]?.id
      || ""
    ));
  }

  async function refreshOrganizationData(organizationId: string) {
    const base = organizationPath(organizationId);
    const [organizationResponse, membersResponse, seatsResponse, knowledgeResponse] = await Promise.all([
      fetch(base, { cache: "no-store" }),
      fetch(`${base}/members`, { cache: "no-store" }),
      fetch(`${base}/seat-status`, { cache: "no-store" }),
      fetch(`${base}/knowledge-sources`, { cache: "no-store" })
    ]);
    const [organizationPayload, membersPayload, seatsPayload, knowledgePayload] = await Promise.all([
      readJson<Organization>(organizationResponse),
      readJson<{ items: Member[] }>(membersResponse),
      readJson<SeatProjection>(seatsResponse),
      readJson<{ items: KnowledgeSource[] }>(knowledgeResponse)
    ]);
    if (organizationResponse.ok && organizationPayload) setOrganization(organizationPayload);
    const loadedMembers = membersResponse.ok && membersPayload ? membersPayload.items : [];
    setMembers(loadedMembers);
    setSeats(seatsResponse.ok && seatsPayload ? seatsPayload : null);
    setKnowledgeSources(knowledgeResponse.ok && knowledgePayload ? knowledgePayload.items : []);

    const viewerMembership = loadedMembers.find(
      (member) => member.email.toLowerCase() === currentUserEmail.toLowerCase() && member.status === "active"
    );
    if (organizationResponse.ok && organizationPayload?.status === "active" && isManagerRole(viewerMembership?.role)) {
      const invitationResponse = await fetch(`${base}/invitations`, { cache: "no-store" });
      const invitationPayload = await readJson<{ items: Invitation[] }>(invitationResponse);
      setInvitations(invitationResponse.ok && invitationPayload ? invitationPayload.items : []);
    } else {
      setInvitations([]);
    }
  }

  async function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    clearFeedback();
    const response = await fetch("/api/backend/api/organizations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newOrganizationName })
    });
    const payload = await readJson<Organization & { detail?: string }>(response);
    setWorking(false);
    if (!response.ok || !payload) {
      setError(payload?.detail ?? "Organization could not be created.");
      return;
    }
    setNewOrganizationName("");
    setMessage("Organization created.");
    await refreshOrganizations();
    setSelectedId(payload.id);
  }

  async function updateOrganizationName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(organizationPath(selectedId), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: organizationName })
    });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Organization name could not be updated.");
      return;
    }
    setOrganizationName("");
    setMessage("Organization name updated.");
    await refreshOrganizations();
    await refreshOrganizationData(selectedId);
  }

  async function changeOrganizationStatus(status: "active" | "disabled") {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(organizationPath(selectedId), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Organization status could not be updated.");
      return;
    }
    setMessage(status === "active" ? "Organization reactivated." : "Organization disabled.");
    await refreshOrganizations();
    await refreshOrganizationData(selectedId);
  }

  async function inviteMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/invitations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: inviteEmail, role: inviteRole })
    });
    const payload = await readJson<Invitation & { token?: string; detail?: string }>(response);
    setWorking(false);
    if (!response.ok || !payload) {
      setError(invitationError(payload?.detail));
      return;
    }
    setInviteEmail("");
    if (payload.token) {
      setOneTimeInvitation({ invitationId: payload.id, destinationEmail: payload.destination_email, token: payload.token, action: "created" });
      setMessage("Invitation created. The one-time link is available below.");
    } else {
      setOneTimeInvitation(null);
      setMessage("A pending invitation already exists for that email. No token was returned.");
    }
    await refreshOrganizationData(selectedId);
  }

  async function resendInvitation(invitation: Invitation) {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/invitations/${encodeURIComponent(invitation.id)}/resend`, { method: "POST" });
    const payload = await readJson<Invitation & { token?: string; detail?: string }>(response);
    setWorking(false);
    if (!response.ok || !payload?.token) {
      setError(invitationError(payload?.detail));
      return;
    }
    setOneTimeInvitation({ invitationId: payload.id, destinationEmail: payload.destination_email, token: payload.token, action: "resent" });
    setMessage("Invitation resent. The earlier token is no longer valid.");
    await refreshOrganizationData(selectedId);
  }

  async function revokeInvitation(invitation: Invitation) {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/invitations/${encodeURIComponent(invitation.id)}/revoke`, { method: "POST" });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Invitation could not be revoked.");
      return;
    }
    setOneTimeInvitation((current) => current?.invitationId === invitation.id ? null : current);
    setMessage("Invitation revoked. Seat usage has been refreshed.");
    await refreshOrganizationData(selectedId);
  }

  async function updateMember(member: Member, nextRole: string) {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/members/${encodeURIComponent(member.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: nextRole })
    });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Member role could not be updated.");
      return;
    }
    setMessage("Member role updated.");
    await refreshOrganizationData(selectedId);
  }

  async function removeMember(member: Member) {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/members/${encodeURIComponent(member.id)}`, { method: "DELETE" });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Member could not be removed.");
      return;
    }
    setMessage("Member removed.");
    await refreshOrganizationData(selectedId);
  }

  async function confirmLifecycleOrTransfer() {
    if (!confirmation || !selectedId) return;
    const action = confirmation;
    setWorking(true);
    clearFeedback();
    if (action.kind === "delete") {
      const response = await fetch(organizationPath(selectedId), { method: "DELETE" });
      const payload = await readJson<{ detail?: string }>(response);
      setWorking(false);
      if (!response.ok) {
        setError(payload?.detail ?? "Organization could not be deleted.");
        return;
      }
      setConfirmation(null);
      setMessage("Organization deleted.");
      setSelectedId("");
      await refreshOrganizations();
      return;
    }
    const response = await fetch(`${organizationPath(selectedId)}/transfer-ownership`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_membership_id: action.target.id })
    });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setConfirmation(null);
      setError(payload?.detail === "Recent authentication required" ? "Reauthenticate to transfer ownership, then retry this transfer." : payload?.detail ?? "Ownership could not be transferred.");
      return;
    }
    setConfirmation(null);
    setMessage(`${action.target.email} is now the organization owner. Your role is now admin.`);
    await refreshOrganizationData(selectedId);
  }

  async function exportOrganization() {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/export`, { cache: "no-store" });
    setWorking(false);
    if (!response.ok) {
      const payload = await readJson<{ detail?: string }>(response);
      setError(payload?.detail ?? "Organization export is unavailable for this role.");
      return;
    }
    const blob = new Blob([JSON.stringify(await response.json(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selectedOrganization?.slug ?? "organization"}-export.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setMessage("Organization export download started.");
  }

  async function copyInvitationLink() {
    if (!oneTimeInvitation) return;
    try {
      await navigator.clipboard.writeText(invitationUrl(oneTimeInvitation.token));
      setCopyMessage("Invitation link copied.");
    } catch {
      setCopyMessage("Copy is unavailable in this browser. Select the link and copy it manually.");
    }
  }

  async function createKnowledgeSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/knowledge-sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: sourceTitle, protocol: sourceProtocol, source_type: "documentation", source_url: sourceUrl, approval_confirmed: approvalConfirmed, approval_notes: approvalNotes || null })
    });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Knowledge source metadata could not be registered.");
      return;
    }
    setSourceTitle("");
    setSourceProtocol("");
    setSourceUrl("");
    setApprovalNotes("");
    setApprovalConfirmed(false);
    setMessage("Knowledge source metadata registered.");
    await refreshOrganizationData(selectedId);
  }

  async function removeKnowledgeSource(sourceId: string) {
    if (!selectedId) return;
    setWorking(true);
    clearFeedback();
    const response = await fetch(`${organizationPath(selectedId)}/knowledge-sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" });
    const payload = await readJson<{ detail?: string }>(response);
    setWorking(false);
    if (!response.ok) {
      setError(payload?.detail ?? "Knowledge source metadata could not be removed.");
      return;
    }
    setMessage("Knowledge source metadata removed.");
    await refreshOrganizationData(selectedId);
  }

  function clearFeedback() {
    setError("");
    setMessage("");
    setCopyMessage("");
  }

  return (
    <section className="stack organization-workspace" aria-busy={working}>
      <form className="form-panel auth-form" onSubmit={createOrganization}>
        <h2>Create organization</h2>
        <label htmlFor="organization-name">Name<input id="organization-name" onChange={(event) => setNewOrganizationName(event.target.value)} required value={newOrganizationName} /></label>
        <button className="primary-action" disabled={working} type="submit">Create</button>
      </form>

      <section className="panel">
        <div className="section-toolbar"><div><h2>Organizations</h2><p>Select an organization workspace.</p></div>{selectedId ? <Link className="secondary-link" href={`/organizations/${encodeURIComponent(selectedId)}`}>Open workspace</Link> : null}</div>
        {organizations.length ? <label htmlFor="organization-selector">Organization<select id="organization-selector" onChange={(event) => setSelectedId(event.target.value)} value={selectedId}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.status})</option>)}</select></label> : <p>No organizations available for this account.</p>}
      </section>

      {selectedOrganization ? <>
        <section className="panel organization-overview">
          <div className="section-toolbar"><div><p className="eyebrow">Organization</p><h2>{selectedOrganization.name}</h2><p>Current role: <strong>{currentMembership?.role ?? "No active role"}</strong></p></div><span className={`status-badge status-${isActive ? "info" : "warning"}`}>{selectedOrganization.status}</span></div>
          {seats ? <div className="seat-summary" aria-label="Organization seat usage"><strong>{seats.consumed} / {seats.limit} seats</strong><dl className="seat-breakdown"><div><dt>Active</dt><dd>{seats.active}</dd></div><div><dt>Reserved</dt><dd>{seats.reserved}</dd></div><div><dt>Consumed</dt><dd>{seats.consumed}</dd></div><div><dt>Remaining</dt><dd>{seats.remaining}</dd></div></dl></div> : <p className="muted-small">Seat projection is unavailable for this organization state.</p>}
        </section>
        {!isActive ? <section className="notice" role="status"><h2>Organization disabled</h2><p>Membership, invitation, and ownership transfer operations are unavailable while this organization is disabled.</p></section> : null}

        {canManage ? <form className="form-panel auth-form" onSubmit={updateOrganizationName}><h2>Organization settings</h2><label htmlFor="organization-display-name">Name<input id="organization-display-name" onChange={(event) => setOrganizationName(event.target.value)} placeholder={selectedOrganization.name} required value={organizationName} /></label><button className="secondary-action" disabled={working} type="submit">Update name</button></form> : null}

        <section className="panel"><h2>Active members</h2>{activeMembers.length ? <div className="table-wrap"><table><thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>{activeMembers.map((member) => <tr key={member.id}><td><strong>{member.email}</strong></td><td>{member.role}</td><td>{member.status}</td><td>{canManage && member.role !== "owner" ? <div className="table-actions"><label className="sr-only" htmlFor={`member-role-${member.id}`}>Role for {member.email}</label><select id={`member-role-${member.id}`} onChange={(event) => void updateMember(member, event.target.value)} value={roleOptions.includes(member.role as (typeof roleOptions)[number]) ? member.role : "member"}>{roleOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select><button className="secondary-action" disabled={working} onClick={() => void removeMember(member)} type="button">Remove</button></div> : <span className="muted-small">No ordinary role action</span>}</td></tr>)}</tbody></table></div> : <p>No active memberships are available.</p>}</section>

        {canManage ? <>
          <form className="form-panel auth-form" onSubmit={inviteMember}><h2>Invite member</h2><div className="manual-grid"><label htmlFor="invite-email">Destination email<input autoComplete="email" id="invite-email" onChange={(event) => setInviteEmail(event.target.value)} required type="email" value={inviteEmail} /></label><label htmlFor="invite-role">Invitation role<select id="invite-role" onChange={(event) => setInviteRole(event.target.value as (typeof roleOptions)[number])} value={inviteRole}>{roleOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select></label></div><button className="primary-action" disabled={working} type="submit">Create invitation</button></form>
          {oneTimeInvitation ? <section className="panel invitation-token-panel" aria-labelledby="one-time-invitation-title"><h2 id="one-time-invitation-title">One-time invitation link</h2><p>{oneTimeInvitation.action === "resent" ? "A replacement link was created. The earlier link is invalid." : "This link is available only in the current page state."}</p><label htmlFor="one-time-invitation-link">Invitation link for {oneTimeInvitation.destinationEmail}<input id="one-time-invitation-link" readOnly value={invitationUrl(oneTimeInvitation.token)} /></label><div className="action-row compact-actions"><button className="secondary-action" onClick={() => void copyInvitationLink()} type="button">Copy invitation link</button><button className="secondary-action" onClick={() => setOneTimeInvitation(null)} type="button">Dismiss</button></div><p className="muted-small" role="status">{copyMessage}</p></section> : null}
          <section className="panel"><h2>Invitations</h2>{invitations.length ? <div className="table-wrap"><table><thead><tr><th>Destination</th><th>Role</th><th>Status</th><th>Expires</th><th>Actions</th></tr></thead><tbody>{invitations.map((invitation) => <tr key={invitation.id}><td><strong>{invitation.destination_email}</strong></td><td>{invitation.role}</td><td>{invitation.status}</td><td>{formatDate(invitation.expires_at)}</td><td>{invitation.status === "pending" ? <div className="table-actions"><button className="secondary-action" disabled={working} onClick={() => void resendInvitation(invitation)} type="button">Resend</button><button className="secondary-action" disabled={working} onClick={() => void revokeInvitation(invitation)} type="button">Revoke</button></div> : <span className="muted-small">No action</span>}</td></tr>)}</tbody></table></div> : <p>No invitations are available.</p>}</section>
        </> : null}

        {isActive && isOwner ? <section className="panel"><h2>Ownership transfer</h2><p>Select an active member. They become owner and your role becomes admin.</p>{transferTargets.length ? <div className="action-row compact-actions"><label htmlFor="ownership-target">Active member<select id="ownership-target" onChange={(event) => setTransferTargetId(event.target.value)} value={transferTargetId}>{transferTargets.map((member) => <option key={member.id} value={member.id}>{member.email} ({member.role})</option>)}</select></label><button className="secondary-action" disabled={working || !transferTargetId} onClick={() => { const target = transferTargets.find((member) => member.id === transferTargetId); if (target) setConfirmation({ kind: "transfer", target }); }} type="button">Transfer ownership</button></div> : <p>No other active member is available for transfer.</p>}</section> : null}

        {isOwner ? <section className="panel"><h2>Organization lifecycle</h2><div className="action-row compact-actions">{isActive ? <button className="secondary-action" disabled={working} onClick={() => void changeOrganizationStatus("disabled")} type="button">Disable organization</button> : <button className="secondary-action" disabled={working} onClick={() => void changeOrganizationStatus("active")} type="button">Reactivate organization</button>}<button className="secondary-action" disabled={working || !canExport} onClick={() => void exportOrganization()} type="button">Export organization data</button><button className="secondary-action" disabled={working} onClick={() => setConfirmation({ kind: "delete" })} type="button">Delete organization</button></div></section> : null}

        {canExport && !isOwner ? <section className="panel organization-export"><h2>Organization export</h2><p>Download the organization data available to your active administrator role.</p><button className="secondary-action" disabled={working} onClick={() => void exportOrganization()} type="button">Export organization data</button></section> : null}

        {isActive && isManager ? <><section className="panel"><h2>Approved knowledge sources</h2>{knowledgeSources.length ? <ul className="knowledge-source-list">{knowledgeSources.map((source) => <li key={source.id}><div><strong>{source.title}</strong><span>{source.protocol} · {source.approval_status} · {source.storage_status}</span><a className="text-link" href={source.source_url} rel="noreferrer" target="_blank">Open source</a></div><button className="secondary-action" disabled={working} onClick={() => void removeKnowledgeSource(source.id)} type="button">Remove</button></li>)}</ul> : <p>No organization knowledge source metadata is registered.</p>}</section><form className="form-panel auth-form" onSubmit={createKnowledgeSource}><h2>Register knowledge source</h2><div className="manual-grid"><label htmlFor="knowledge-source-title">Title<input id="knowledge-source-title" maxLength={255} onChange={(event) => setSourceTitle(event.target.value)} required value={sourceTitle} /></label><label htmlFor="knowledge-source-protocol">Protocol<input id="knowledge-source-protocol" maxLength={64} onChange={(event) => setSourceProtocol(event.target.value)} required value={sourceProtocol} /></label></div><label htmlFor="knowledge-source-url">Source URL<input id="knowledge-source-url" onChange={(event) => setSourceUrl(event.target.value)} required type="url" value={sourceUrl} /></label><label htmlFor="knowledge-source-notes">Approval notes<textarea id="knowledge-source-notes" maxLength={2000} onChange={(event) => setApprovalNotes(event.target.value)} rows={3} value={approvalNotes} /></label><label className="checkbox-row" htmlFor="knowledge-source-approved"><input checked={approvalConfirmed} id="knowledge-source-approved" onChange={(event) => setApprovalConfirmed(event.target.checked)} required type="checkbox" />I reviewed this source and approve its provenance metadata for the organization.</label><button className="primary-action" disabled={working} type="submit">Register source</button></form></> : null}
      </> : null}

      {error ? <p className="error-text" role="alert">{error}{error === "Reauthenticate to transfer ownership, then retry this transfer." ? <> <Link className="text-link" href="/login">Log in again</Link></> : null}</p> : null}
      {message ? <p className="success-text" role="status">{message}</p> : null}
      {confirmation ? <dialog aria-labelledby="organization-confirmation-title" aria-modal="true" className="confirmation-dialog" onCancel={() => setConfirmation(null)} ref={confirmationDialogRef}><h2 id="organization-confirmation-title">{confirmation.kind === "delete" ? "Delete organization" : "Transfer ownership"}</h2><p>{confirmation.kind === "delete" ? "Delete this organization and revoke its pending invitations? This cannot be undone from the workspace." : `${confirmation.target.email} becomes owner and your role becomes admin.`}</p><div className="action-row compact-actions"><button autoFocus className="secondary-action" disabled={working} onClick={() => setConfirmation(null)} type="button">Cancel</button><button className="primary-action" disabled={working} onClick={() => void confirmLifecycleOrTransfer()} type="button">{confirmation.kind === "delete" ? "Delete organization" : "Confirm transfer"}</button></div></dialog> : null}
    </section>
  );
}

function organizationPath(organizationId: string): string { return `/api/backend/api/organizations/${encodeURIComponent(organizationId)}`; }
function isManagerRole(role: string | undefined): boolean { return role === "owner" || role === "admin"; }
function invitationError(detail: string | undefined): string {
  return detail?.toLowerCase().includes("seat limit") ? "All organization seats are currently consumed. Revoke an invitation or wait for one to expire before inviting another member." : detail ?? "Invitation could not be completed.";
}
function invitationUrl(token: string): string { return typeof window === "undefined" ? token : `${window.location.origin}/organization-invitations/accept?token=${encodeURIComponent(token)}`; }
function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(); }
async function readJson<T>(response: Response): Promise<T | null> { try { return await response.json() as T; } catch { return null; } }
