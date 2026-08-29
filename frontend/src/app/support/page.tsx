import { SupportWorkspace } from "@/components/SupportWorkspace";

export default function SupportPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Account</p>
        <h1>Support and Requests</h1>
        <p>Create and review private requests that belong only to your account.</p>
      </section>
      <SupportWorkspace />
    </main>
  );
}
