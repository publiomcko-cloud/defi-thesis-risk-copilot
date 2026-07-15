import Link from "next/link";

type PublicAdminBoundaryProps = {
  title: string;
  description: string;
};

export function PublicAdminBoundary({ title, description }: PublicAdminBoundaryProps) {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Protected product area</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </section>
      <section className="notice">
        <h2>Unavailable in the public deployment</h2>
        <p>
          This capability requires an authenticated private environment. The hosted
          portfolio demo exposes workflow evidence and safe metadata without granting
          privileged access.
        </p>
      </section>
      <div className="action-row">
        <Link className="primary-link" href="/demo">Return to Demo</Link>
        <Link className="secondary-link" href="/review">View Read-Only Review Flow</Link>
      </div>
    </main>
  );
}
