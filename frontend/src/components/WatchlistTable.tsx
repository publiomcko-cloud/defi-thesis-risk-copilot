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

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

const defaultRules = {
  borrow_apy_above_threshold: "8",
  net_spread_below_threshold: "2",
  liquidity_below_threshold: "500000"
};

const defaultSnapshot = {
  borrow_apy: "10",
  net_spread_apy: "1",
  liquidity_usd: "250000"
};

const percentageKeys = new Set([
  "borrow_apy_above_threshold",
  "net_spread_below_threshold",
  "borrow_apy",
  "net_spread_apy"
]);

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
    setError(null);
    try {
      const [watchlist, alertEvents] = await Promise.all([
        fetchWatchlistItems(),
        fetchAlertEvents()
      ]);
      setItems(watchlist.items);
      setAlerts(alertEvents.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Watchlist data failed to load.");
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveId("create");
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
    } finally {
      setActiveId(null);
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
      {publicDemoMode ? (
        <section className="notice">
          <h2>Read-only demonstration</h2>
          <p>
            The hosted demo displays seeded monitoring rules and alerts. Creating,
            changing, evaluating, or acknowledging records is disabled for public visitors.
          </p>
        </section>
      ) : (
        <form className="form-panel" onSubmit={handleCreate}>
          <label>
            Watch title
            <input maxLength={255} onChange={(event) => setTitle(event.target.value)} value={title} />
          </label>
          <label>
            Protocol
            <input maxLength={64} onChange={(event) => setProtocol(event.target.value)} value={protocol} />
          </label>
          <fieldset>
            <legend>Rule thresholds</legend>
            <p className="field-help">Percentage values use normal units: 8 means 8%.</p>
            <div className="manual-grid">
              {Object.entries(rules).map(([key, value]) => (
                <label key={key}>
                  {humanize(key)}{percentageKeys.has(key) ? " (%)" : ""}
                  <input
                    inputMode="decimal"
                    min="0"
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
            <legend>Current snapshot</legend>
            <div className="manual-grid">
              {Object.entries(snapshot).map(([key, value]) => (
                <label key={key}>
                  {humanize(key)}{percentageKeys.has(key) ? " (%)" : ""}
                  <input
                    inputMode="decimal"
                    min="0"
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
          {error ? <p className="error" role="alert">{error}</p> : null}
          {message ? <p className="success">{message}</p> : null}
          <button className="primary-action" disabled={activeId !== null} type="submit">
            {activeId === "create" ? "Adding..." : "Add Watch"}
          </button>
        </form>
      )}

      {publicDemoMode && error ? <p className="error" role="alert">{error}</p> : null}

      <section className="panel">
        <div className="section-toolbar">
          <div>
            <h2>Watchlist</h2>
            <p>Stored thresholds are shown in human-readable units.</p>
          </div>
          <button className="secondary-action" onClick={() => void refresh()} type="button">
            Refresh
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Rules</th>
                <th>Snapshot</th>
                {!publicDemoMode ? <th>Action</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={publicDemoMode ? 3 : 4}>No watchlist items yet.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.title}</strong>
                      <span>{item.protocol ?? item.item_type}</span>
                    </td>
                    <td>{renderValues(item.rules)}</td>
                    <td>{renderValues(item.snapshot)}</td>
                    {!publicDemoMode ? (
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
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <AlertEventsPanel alerts={alerts} onUpdated={refresh} readOnly={publicDemoMode} />
    </div>
  );
}

function numberMap(values: Record<string, string>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([, value]) => value.trim() !== "")
      .map(([key, value]) => [
        key,
        percentageKeys.has(key) ? Number(value) / 100 : Number(value)
      ])
  );
}

function renderValues(values: Record<string, unknown>) {
  return (
    <ul className="compact-list">
      {Object.entries(values).map(([key, value]) => (
        <li key={key}>
          <strong>{humanize(key)}:</strong> {formatValue(key, value)}
        </li>
      ))}
    </ul>
  );
}

function formatValue(key: string, value: unknown): string {
  if (typeof value !== "number") {
    return String(value);
  }
  if (percentageKeys.has(key)) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (key.includes("usd") || key.includes("liquidity")) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0
    }).format(value);
  }
  return String(value);
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
