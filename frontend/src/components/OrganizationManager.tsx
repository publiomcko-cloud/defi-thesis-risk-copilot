"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Organization = { id: string; name: string; slug: string; status: string };
type Member = { id: string; email: string; role: string; status: string };
type KnowledgeSource = {
  id: string;
  title: string;
  protocol: string;
  source_type: string;
  source_url: string;
  approval_status: string;
  storage_status: string;
  status: string;
};

export function OrganizationManager({ initialOrganizationId }: { initialOrganizationId?: string }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selected, setSelected] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [currentUserEmail, setCurrentUserEmail] = useState("");
  const [name, setName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceProtocol, setSourceProtocol] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [approvalNotes, setApprovalNotes] = useState("");
  const [approvalConfirmed, setApprovalConfirmed] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void refreshOrganizations();
    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => response.json())
      .then((payload) => setCurrentUserEmail(payload.user?.email ?? ""))
      .catch(() => setCurrentUserEmail(""));
  }, []);

  useEffect(() => {
    if (selected) {
      setMembers([]);
      setKnowledgeSources([]);
      void refreshMembers(selected);
      void refreshKnowledgeSources(selected);
    }
  }, [selected]);

  async function refreshOrganizations() {
    const response = await fetch("/api/backend/api/organizations", { cache: "no-store" });
    if (response.ok) {
      const payload = await response.json();
      setOrganizations(payload.items);
      setSelected((current) => current || payload.items.find((item: Organization) => item.id === initialOrganizationId)?.id || payload.items[0]?.id || "");
    }
  }

  async function refreshMembers(orgId: string) {
    const response = await fetch(`/api/backend/api/organizations/${orgId}/members`, { cache: "no-store" });
    if (response.ok) {
      setMembers((await response.json()).items);
    }
  }

  async function refreshKnowledgeSources(orgId: string) {
    const response = await fetch(`/api/backend/api/organizations/${orgId}/knowledge-sources`, { cache: "no-store" });
    if (response.ok) {
      setKnowledgeSources((await response.json()).items);
    } else {
      setKnowledgeSources([]);
    }
  }

  async function createOrg(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/backend/api/organizations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    setMessage(response.ok ? "Organization created." : "Sign in to create organizations.");
    setName("");
    await refreshOrganizations();
  }

  async function inviteMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const response = await fetch(`/api/backend/api/organizations/${selected}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role })
    });
    setMessage(response.ok ? "Member invitation saved." : "Unable to add member.");
    setEmail("");
    await refreshMembers(selected);
  }

  async function updateOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const response = await fetch(`/api/backend/api/organizations/${selected}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: organizationName })
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Organization updated." : body.detail ?? "Unable to update organization.");
    if (response.ok) {
      setOrganizationName("");
      await refreshOrganizations();
    }
  }

  async function updateMember(member: Member, nextRole: string) {
    if (!selected) {
      return;
    }
    const response = await fetch(`/api/backend/api/organizations/${selected}/members/${member.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: nextRole })
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Member role updated." : body.detail ?? "Unable to update member.");
    if (response.ok) {
      await refreshMembers(selected);
    }
  }

  async function removeMember(member: Member) {
    if (!selected || !window.confirm(`Remove ${member.email} from this organization?`)) {
      return;
    }
    const response = await fetch(`/api/backend/api/organizations/${selected}/members/${member.id}`, { method: "DELETE" });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Member removed." : body.detail ?? "Unable to remove member.");
    if (response.ok) {
      await refreshMembers(selected);
    }
  }

  async function createKnowledgeSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const response = await fetch(`/api/backend/api/organizations/${selected}/knowledge-sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: sourceTitle,
        protocol: sourceProtocol,
        source_type: "documentation",
        source_url: sourceUrl,
        approval_confirmed: approvalConfirmed,
        approval_notes: approvalNotes || null
      })
    });
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Knowledge source metadata registered." : body.detail ?? "Unable to register knowledge source metadata.");
    if (!response.ok) {
      return;
    }
    setSourceTitle("");
    setSourceProtocol("");
    setSourceUrl("");
    setApprovalNotes("");
    setApprovalConfirmed(false);
    await refreshKnowledgeSources(selected);
  }

  async function removeKnowledgeSource(sourceId: string) {
    if (!selected || !window.confirm("Remove this knowledge source metadata?")) {
      return;
    }
    const response = await fetch(
      `/api/backend/api/organizations/${selected}/knowledge-sources/${encodeURIComponent(sourceId)}`,
      { method: "DELETE" }
    );
    const body = await response.json().catch(() => ({}));
    setMessage(response.ok ? "Knowledge source metadata removed." : body.detail ?? "Unable to remove knowledge source metadata.");
    if (response.ok) {
      await refreshKnowledgeSources(selected);
    }
  }

  const canManageKnowledge = members.some(
    (member) => member.email === currentUserEmail
      && member.status === "active"
      && (member.role === "owner" || member.role === "admin")
  );
  const canManageMembers = canManageKnowledge;
  const selectedOrganization = organizations.find((organization) => organization.id === selected);

  return (
    <section className="stack">
      <form className="form-panel auth-form" onSubmit={createOrg}>
        <h2>Create Organization</h2>
        <label>
          Name
          <input onChange={(event) => setName(event.target.value)} required value={name} />
        </label>
        <button className="primary-action" type="submit">Create</button>
      </form>
      <section className="panel">
        <h2>Organizations</h2>
        <select onChange={(event) => setSelected(event.target.value)} value={selected}>
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>{org.name} ({org.status})</option>
          ))}
        </select>
        {selected ? <Link className="secondary-link" href={`/organizations/${selected}`}>Open organization</Link> : null}
        {!organizations.length ? <p>No organizations available for this account.</p> : null}
      </section>
      {selected ? (
        <>
          {canManageMembers ? (
            <form className="form-panel auth-form" onSubmit={updateOrganization}>
              <h2>Organization settings</h2>
              <label>
                Name
                <input onChange={(event) => setOrganizationName(event.target.value)} placeholder={selectedOrganization?.name} required value={organizationName} />
              </label>
              <button className="secondary-action" type="submit">Update name</button>
            </form>
          ) : null}
          <form className="form-panel auth-form" onSubmit={inviteMember}>
            <h2>Members</h2>
            <ul className="compact-list">
              {members.map((member) => (
                <li key={member.id}>
                  <span>{member.email} · {member.role} · {member.status}</span>
                  {canManageMembers && member.status !== "removed" ? (
                    <span className="action-row compact-actions">
                      <select aria-label={`Role for ${member.email}`} defaultValue={member.role} onChange={(event) => void updateMember(member, event.target.value)}>
                        <option value="viewer">Viewer</option>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                        <option value="owner">Owner</option>
                      </select>
                      <button className="secondary-action" onClick={() => void removeMember(member)} type="button">Remove</button>
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
            <label>
              Invite email
              <input onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
            </label>
            <label>
              Role
              <select onChange={(event) => setRole(event.target.value)} value={role}>
                <option value="viewer">Viewer</option>
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="owner">Owner</option>
              </select>
            </label>
            <button className="primary-action" type="submit">Invite</button>
          </form>

          <section className="panel">
            <h2>Approved Knowledge Sources</h2>
            {knowledgeSources.length ? (
              <ul className="knowledge-source-list">
                {knowledgeSources.map((source) => (
                  <li key={source.id}>
                    <div>
                      <strong>{source.title}</strong>
                      <span>{source.protocol} · {source.approval_status} · {source.storage_status}</span>
                      <a className="text-link" href={source.source_url} rel="noreferrer" target="_blank">Open source</a>
                    </div>
                    {canManageKnowledge ? (
                      <button className="secondary-action" onClick={() => removeKnowledgeSource(source.id)} type="button">Remove</button>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No organization knowledge source metadata is registered.</p>
            )}
          </section>

          {canManageKnowledge ? (
            <form className="form-panel auth-form" onSubmit={createKnowledgeSource}>
              <h2>Register Knowledge Source</h2>
              <div className="manual-grid">
                <label>
                  Title
                  <input maxLength={255} onChange={(event) => setSourceTitle(event.target.value)} required value={sourceTitle} />
                </label>
                <label>
                  Protocol
                  <input maxLength={64} onChange={(event) => setSourceProtocol(event.target.value)} required value={sourceProtocol} />
                </label>
              </div>
              <label>
                Source URL
                <input onChange={(event) => setSourceUrl(event.target.value)} required type="url" value={sourceUrl} />
              </label>
              <label>
                Approval notes
                <textarea maxLength={2000} onChange={(event) => setApprovalNotes(event.target.value)} rows={3} value={approvalNotes} />
              </label>
              <label className="checkbox-row">
                <input
                  checked={approvalConfirmed}
                  onChange={(event) => setApprovalConfirmed(event.target.checked)}
                  required
                  type="checkbox"
                />
                I reviewed this source and approve its provenance metadata for the organization.
              </label>
              <p className="muted-small">Metadata only. Organization document and vector storage is not enabled.</p>
              <button className="primary-action" type="submit">Register source</button>
            </form>
          ) : null}
        </>
      ) : null}
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
