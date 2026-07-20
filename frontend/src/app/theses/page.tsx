import Link from "next/link";

export default function ThesesPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Saved theses</p>
        <h1>Private strategy workspace</h1>
        <p>Authenticated users can save, revisit, update, and analyze strategy theses without exposing them to other users.</p>
      </section>
      <section className="content-grid">
        <article className="panel">
          <h2>Ownership</h2>
          <p>Saved theses are private by default and may be scoped to an organization when the user has an active membership.</p>
        </article>
        <article className="panel">
          <h2>Analysis path</h2>
          <p>Theses can be used as source text for deterministic analysis while preserving the existing non-advisory safety boundary.</p>
        </article>
      </section>
      <Link className="primary-link" href="/analyze">Start analysis</Link>
    </main>
  );
}
