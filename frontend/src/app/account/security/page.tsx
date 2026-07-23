import { MfaSecurityPanel } from "@/components/MfaSecurityPanel";

export default function AccountSecurityPage() {
  const mfaRequired = process.env.ADMIN_MFA_REQUIRED === "true";
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Security</p>
        <h1>Account security</h1>
        <p>Enroll a TOTP authenticator, verify this session, and manage the factors attached to your Supabase identity.</p>
      </section>
      <MfaSecurityPanel adminMfaRequired={mfaRequired} />
    </main>
  );
}
