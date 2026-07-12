"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  createWatchlistItem,
  evaluateWatchlistItem,
  fetchAlertEvents,
  fetchWatchlistItems
} from "@/lib/api";
import type { AlertEvent, WatchlistItem } from "@/lib/types";
import { AlertEventsPanel } from "./AlertEventsPanel";

const defaultRules = {
  borrow_apy_above_threshold: "0.08",
  net_spread_below_threshold: "0.02",
  liquidity_below_threshold: "500000"
};

const defaultSnapshot = {
  borrow_apy: "0.1",
  net_spread_apy: "0.01",
  liquidity_usd: "250000"
};

export function WatchlistTable() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [title, setTitle] = useState("Pendle Morpho spread watch");
  const [protocol, setProtocol] = useState("pendle");
  const [rules, setRules] = useState(defaultRules);
  const [snapshot, setSnapshot] = useState(defaultSnapshot);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    const [watchlist, alertEvents] = await Promise.all([
      fetchWatchlistItems(),
      fetchAlertEvents()
    ]);
    setItems(watchlist.items);
    setAlerts(alertEvents.items);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createWatchlistItem({
        item_type: "strategy",
        title,
        protocol,
        rules: numberMap(rules),
        snapshot: numberMap(snapshot)
      });
      setMessage("Watchlist item created.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Watchlist creation failed.");
    }
  }

  async function handleEvaluate(itemId: string) {
    setActiveId(itemId);
    setError(null);
    setMessage(null);
    try {
      const result = await evaluateWatchlistItem(itemId);
      setMessage(`Evaluated ${result.evaluated_rules.length} rules and created ${result.created_alerts.length} alerts.`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Watchlist evaluation failed.");
    } finally {
      setActiveId(null);
    }
  }

  return (
    <div className="stack">
      <form className="form-panel" onSubmit={handleCreate}>
        <label>
          Watch title
          <input onChange={(event) => setTitle(event.target.value)} value={title} />
        </label>
        <label>
          Protocol
          <input onChange={(event) => setProtocol(event.target.value)} value={protocol} />
        </label>
        <fieldset>
          <legend>Rule Thresholds</legend>
          <div className="manual-grid">
            {Object.entries(rules).map(([key, value]) => (
              <label key={key}>
                {key}
                <input
                  inputMode="decimal"
                  onChange={(event) =>
                    setRules((current) => ({ ...current, [key]: event.target.value }))
                  }
                  step="any"
                  type="number"
                  value={value}
                />
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>Current Snapshot</legend>
          <div className="manual-grid">
            {Object.entries(snapshot).map(([key, value]) => (
              <label key={key}>
                {key}
                <input
                  inputMode="decimal"
                  onChange={(event) =>
                    setSnapshot((current) => ({ ...current, [key]: event.target.value }))
                  }
                  step="any"
                  type="number"
                  value={value}
                />
              </label>
            ))}
          </div>
        </fieldset>
        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="success">{message}</p> : null}
        <button className="primary-action" type="submit">
          Add Watch
        </button>
      </form>

      <section className="panel">
        <h2>Watchlist</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Rules</th>
                <th>Snapshot</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={4}>No watchlist items yet.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.title}</strong>
                      <span>{item.protocol ?? item.item_type}</span>
                    </td>
                    <td>
                      <code>{JSON.stringify(item.rules)}</code>
                    </td>
                    <td>
                      <code>{JSON.stringify(item.snapshot)}</code>
                    </td>
                    <td>
                      <button
                        className="secondary-action"
                        disabled={activeId !== null}
                        onClick={() => handleEvaluate(item.id)}
                        type="button"
                      >
                        {activeId === item.id ? "Evaluating..." : "Evaluate Rules"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <AlertEventsPanel alerts={alerts} onUpdated={refresh} />
    </div>
  );
}

function numberMap(values: Record<string, string>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value.trim() !== "")
      .map(([key, value]) => [key, Number(value)])
  );
}
