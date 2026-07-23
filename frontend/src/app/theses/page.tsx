import Link from "next/link";
import { ThesisManager } from "@/components/ThesisManager";

export default function ThesesPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Saved theses</p>
        <h1>Private strategy workspace</h1>
        <p>Authenticated users can save, revisit, update, and analyze strategy theses without exposing them to other users.</p>
      </section>
      <ThesisManager />
      <Link className="primary-link" href="/analyze">Start analysis</Link>
    </main>
  );
}
