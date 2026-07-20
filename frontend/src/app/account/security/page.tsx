export default function AccountSecurityPage() {
  const mfaRequired = process.env.ADMIN_MFA_REQUIRED === "true";
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Security</p>
        <h1>Account security</h1>
        <p>Supabase-backed MFA enrollment and challenge verification are supported by the product architecture when enabled in the identity provider.</p>
      </section>
      <section className="stack">
        <article className="panel">
          <h2>MFA status</h2>
          <p>{mfaRequired ? "Platform administrators must complete MFA." : "MFA is optional unless required for platform administrators."}</p>
        </article>
        <article className="notice">
          <h2>External setup required</h2>
          <p>TOTP enrollment and challenge verification require Supabase MFA configuration. Local tests use mocked provider responses.</p>
        </article>
      </section>
    </main>
  );
}
