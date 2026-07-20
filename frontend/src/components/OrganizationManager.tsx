"use client";

import { FormEvent, useEffect, useState } from "react";

type Organization = { id: string; name: string; slug: string; status: string };
type Member = { id: string; email: string; role: string; status: string };

export function OrganizationManager() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selected, setSelected] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void refreshOrganizations();
  }, []);

  useEffect(() => {
    if (selected) {
      void refreshMembers(selected);
    }
  }, [selected]);

  async function refreshOrganizations() {
    const response = await fetch("/api/backend/api/organizations", { cache: "no-store" });
    if (response.ok) {
      const payload = await response.json();
      setOrganizations(payload.items);
      setSelected((current) => current || payload.items[0]?.id || "");
    }
  }

  async function refreshMembers(orgId: string) {
    const response = await fetch(`/api/backend/api/organizations/${orgId}/members`, { cache: "no-store" });
    if (response.ok) {
      setMembers((await response.json()).items);
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
        {!organizations.length ? <p>No organizations available for this account.</p> : null}
      </section>
      {selected ? (
        <form className="form-panel auth-form" onSubmit={inviteMember}>
          <h2>Members</h2>
          <ul className="compact-list">
            {members.map((member) => (
              <li key={member.id}>{member.email} · {member.role} · {member.status}</li>
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
      ) : null}
      {message ? <p className="form-success">{message}</p> : null}
    </section>
  );
}
