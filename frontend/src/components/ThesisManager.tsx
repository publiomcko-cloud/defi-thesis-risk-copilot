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
    const response = await fetch("/api/backend/api/theses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        strategy_text: strategyText,
        protocols: protocols.split(",").map((item) => item.trim()).filter(Boolean),
        assumptions: {},
        visibility: "private"
      })
    });
    setMessage(response.ok ? "Thesis saved." : "Sign in to save theses.");
    if (response.ok) {
      setTitle("");
      setStrategyText("");
      setProtocols("");
      await refresh();
    }
  }

  async function remove(id: string) {
    const response = await fetch(`/api/backend/api/theses/${id}`, { method: "DELETE" });
    setMessage(response.ok ? "Thesis deleted." : "Unable to delete thesis.");
    await refresh();
  }

  return (
    <section className="stack">
      <form className="form-panel auth-form" onSubmit={create}>
        <h2>Save Thesis</h2>
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
        <button className="primary-action" type="submit">Save</button>
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
              <button className="secondary-action" onClick={() => remove(item.id)} type="button">Delete</button>
            </div>
          </article>
        ))}
        {!items.length ? <article className="panel"><h2>No saved theses</h2><p>Saved private strategy notes appear here after login.</p></article> : null}
      </section>
    </section>
  );
}
