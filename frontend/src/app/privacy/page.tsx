export default function PrivacyPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Privacy</p>
        <h1>Privacy policy</h1>
        <p>This draft describes the intended product data handling model and requires qualified legal review before commercial launch.</p>
      </section>
      <section className="stack">
        <article className="panel">
          <h2>Data collected</h2>
          <p>Authenticated accounts may store profile metadata, organization memberships, saved theses, reports, watchlists, consent records, and user-visible audit history.</p>
        </article>
        <article className="panel">
          <h2>Public demo</h2>
          <p>Anonymous demo sessions use isolated temporary identifiers and stricter quotas. Public seeded reports remain shared read-only content.</p>
        </article>
        <article className="panel">
          <h2>Retention and deletion</h2>
          <p>Users can request account export and deletion. Provider identity deletion requires a configured server-side administrative process.</p>
        </article>
      </section>
    </main>
  );
}
