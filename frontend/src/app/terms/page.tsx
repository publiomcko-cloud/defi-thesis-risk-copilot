export default function TermsPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Terms</p>
        <h1>Terms of use</h1>
        <p>This draft is a product foundation and requires qualified legal review before commercial launch.</p>
      </section>
      <section className="stack">
        <article className="panel">
          <h2>Research tooling</h2>
          <p>The service provides educational DeFi research workflows, deterministic risk scoring, source retrieval, and simulations. It does not provide personalized financial, legal, tax, trading, or investment advice.</p>
        </article>
        <article className="panel">
          <h2>No execution</h2>
          <p>The product does not connect wallets, sign transactions, custody assets, or execute trades.</p>
        </article>
        <article className="panel">
          <h2>Accounts</h2>
          <p>Users are responsible for securing their login credentials and complying with applicable laws and organization policies.</p>
        </article>
      </section>
    </main>
  );
}
