import { AuthForm } from "@/components/AuthForm";

export default function ForgotPasswordPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Recovery</p>
        <h1>Recover password</h1>
        <p>For privacy, recovery responses are generic and do not reveal whether an email address exists.</p>
      </section>
      <AuthForm mode="forgot" />
    </main>
  );
}
