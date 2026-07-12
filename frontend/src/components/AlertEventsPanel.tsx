"use client";

import { updateAlertStatus } from "@/lib/api";
import type { AlertEvent } from "@/lib/types";

type AlertEventsPanelProps = {
  alerts: AlertEvent[];
  onUpdated: () => Promise<void>;
};

export function AlertEventsPanel({ alerts, onUpdated }: AlertEventsPanelProps) {
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
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={4}>No alert events yet.</td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>
                    <strong>{alert.title}</strong>
                    <span>{alert.message}</span>
                  </td>
                  <td>
                    <code>{alert.alert_type}</code>
                    <span>{alert.severity}</span>
                  </td>
                  <td>{alert.status}</td>
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
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
