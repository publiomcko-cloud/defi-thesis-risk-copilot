import { OrganizationManager } from "@/components/OrganizationManager";

export default async function OrganizationMembersPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Organization members</p>
        <h1>Membership management</h1>
      </section>
      <OrganizationManager initialOrganizationId={organizationId} />
    </main>
  );
}
