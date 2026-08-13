import { MonitoringSchedulesWorkspace } from "@/components/MonitoringSchedulesWorkspace";

export default function SchedulesPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Account monitoring</p>
        <h1>Schedules</h1>
        <p>Create durable, timezone-aware evaluations for your private watchlist items.</p>
      </section>
      <MonitoringSchedulesWorkspace />
    </main>
  );
}
