import { PublicStatus } from "@/components/PublicStatus";

export default function StatusPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Portfolio status</p>
        <h1>Current Service Status</h1>
        <p>High-level availability for this portfolio surface. It is not an incident-management service.</p>
      </section>
      <PublicStatus />
    </main>
  );
}
