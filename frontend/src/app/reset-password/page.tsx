import { AuthForm } from "@/components/AuthForm";

export default function ResetPasswordPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Recovery</p>
        <h1>Reset password</h1>
        <p>Use the active recovery session from your email link to choose a new password.</p>
      </section>
      <AuthForm mode="reset" />
    </main>
  );
}
