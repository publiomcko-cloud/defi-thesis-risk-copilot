"use client";

import { FormEvent, useEffect, useState } from "react";

type Thesis = {
  id: string;
  title: string;
  strategy_text: string;
  protocols: string[];
  visibility: string;
};

export function ThesisManager() {
  const [items, setItems] = useState<Thesis[]>([]);
  const [title, setTitle] = useState("");
  const [strategyText, setStrategyText] = useState("");
  const [protocols, setProtocols] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    const response = await fetch("/api/backend/api/theses", { cache: "no-store" });
    if (response.ok) {
      setItems((await response.json()).items);
    }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const isEditing = editingId !== null;
    const response = await fetch(isEditing ? `/api/backend/api/theses/${editingId}` : "/api/backend/api/theses", {
      method: isEditing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        strategy_text: strategyText,
        protocols: protocols.split(",").map((item) => item.trim()).filter(Boolean),
        assumptions: {},
        visibility: "private"
      })
    });
    setMessage(response.ok ? (isEditing ? "Thesis updated." : "Thesis saved.") : "Unable to save thesis.");
    if (response.ok) {
      setTitle("");
      setStrategyText("");
      setProtocols("");
      setEditingId(null);
      await refresh();
    }
  }

  function edit(item: Thesis) {
    setEditingId(item.id);
    setTitle(item.title);
    setStrategyText(item.strategy_text);
    setProtocols(item.protocols.join(", "));
    setMessage("");
  }

  function cancelEdit() {
    setEditingId(null);
    setTitle("");
    setStrategyText("");
    setProtocols("");
  }

  async function remove(id: string) {
    const response = await fetch(`/api/backend/api/theses/${id}`, { method: "DELETE" });
    setMessage(response.ok ? "Thesis deleted." : "Unable to delete thesis.");
    await refresh();
  }

  return (
    <section className="stack">
      <form className="form-panel auth-form" onSubmit={create}>
        <h2>{editingId ? "Edit Thesis" : "Save Thesis"}</h2>
        <label>
          Title
          <input onChange={(event) => setTitle(event.target.value)} required value={title} />
        </label>
        <label>
          Strategy text
          <textarea onChange={(event) => setStrategyText(event.target.value)} required rows={6} value={strategyText} />
        </label>
        <label>
          Protocols
          <input onChange={(event) => setProtocols(event.target.value)} placeholder="pendle, morpho" value={protocols} />
        </label>
        <div className="action-row compact-actions">
          <button className="primary-action" type="submit">{editingId ? "Update" : "Save"}</button>
          {editingId ? <button className="secondary-action" onClick={cancelEdit} type="button">Cancel</button> : null}
        </div>
        {message ? <p className="form-success">{message}</p> : null}
      </form>
      <section className="content-grid">
        {items.map((item) => (
          <article className="panel" key={item.id}>
            <h2>{item.title}</h2>
            <p>{item.strategy_text}</p>
            <p className="muted-small">{item.protocols.join(", ") || "No protocol tags"} · {item.visibility}</p>
            <div className="action-row compact-actions">
              <a className="secondary-link" href={`/analyze?thesis=${encodeURIComponent(item.strategy_text)}`}>Analyze</a>
              <button className="secondary-action" onClick={() => edit(item)} type="button">Edit</button>
              <button className="secondary-action" onClick={() => remove(item.id)} type="button">Delete</button>
            </div>
          </article>
        ))}
        {!items.length ? <article className="panel"><h2>No saved theses</h2><p>Saved private strategy notes appear here after login.</p></article> : null}
      </section>
    </section>
  );
}
