import Link from "next/link";

import { AuthForm } from "@/components/AuthForm";

export default function SignupPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Create account</h1>
        <p>Sign up with email verification. This product is research tooling and does not provide personalized financial advice.</p>
      </section>
      <AuthForm mode="signup" />
      <p className="muted-small">
        Already verified? <Link className="text-link" href="/login">Log in</Link>
      </p>
    </main>
  );
}
