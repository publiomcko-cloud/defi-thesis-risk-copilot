import Link from "next/link";

import { AuthForm } from "@/components/AuthForm";

export default function LoginPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Log in</h1>
        <p>Use a verified email account to access private reports, saved theses, and organization resources.</p>
      </section>
      <AuthForm mode="login" />
      <p className="muted-small">
        <Link className="text-link" href="/forgot-password">Forgot password?</Link>{" "}
        <Link className="text-link" href="/signup">Create an account</Link>
      </p>
    </main>
  );
}
