"use client";

import { updateAlertStatus } from "@/lib/api";
import type { AlertEvent } from "@/lib/types";

type AlertEventsPanelProps = {
  alerts: AlertEvent[];
  onUpdated: () => Promise<void>;
  readOnly?: boolean;
};

export function AlertEventsPanel({ alerts, onUpdated, readOnly = false }: AlertEventsPanelProps) {
  async function acknowledge(alertId: string) {
    await updateAlertStatus(alertId, "acknowledged");
    await onUpdated();
  }

  return (
    <section className="panel">
      <h2>In-App Alerts</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Alert</th>
              <th>Type</th>
              <th>Status</th>
              {!readOnly ? <th>Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={readOnly ? 3 : 4}>No alert events yet.</td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>
                    <strong>{alert.title}</strong>
                    <span>{alert.message}</span>
                  </td>
                  <td>
                    <span>{humanize(alert.alert_type)}</span>
                    <span className={`status-badge status-${alert.severity}`}>{alert.severity}</span>
                  </td>
                  <td>
                    <span className="status-badge">{humanize(alert.status)}</span>
                  </td>
                  {!readOnly ? (
                    <td>
                      <button
                        className="secondary-action"
                        disabled={alert.status !== "open"}
                        onClick={() => acknowledge(alert.id)}
                        type="button"
                      >
                        Acknowledge
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
  );
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
