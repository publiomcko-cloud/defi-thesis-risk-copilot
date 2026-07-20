import Link from "next/link";

export default function VerifyEmailPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Verification</p>
        <h1>Check your email</h1>
        <p>Open the verification link sent by Supabase Auth, then return here to log in.</p>
      </section>
      <Link className="primary-link" href="/login">Go to login</Link>
    </main>
  );
}
