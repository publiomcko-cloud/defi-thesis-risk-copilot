import { OrganizationManager } from "@/components/OrganizationManager";

export default function OrganizationsPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Organizations</p>
        <h1>Organization Access</h1>
        <p>Create organizations, manage memberships, and keep organization-scoped research private to active members.</p>
      </section>
      <OrganizationManager />
    </main>
  );
}
