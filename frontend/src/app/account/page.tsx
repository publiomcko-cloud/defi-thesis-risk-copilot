import { AccountPanel } from "@/components/AccountPanel";

export default function AccountPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Account</h1>
        <p>Manage profile, export account data, deletion workflow, and security settings.</p>
      </section>
      <AccountPanel />
    </main>
  );
}
