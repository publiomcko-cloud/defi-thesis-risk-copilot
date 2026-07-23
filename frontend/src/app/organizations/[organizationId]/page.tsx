import { OrganizationManager } from "@/components/OrganizationManager";

export default async function OrganizationDetailPage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Organization</p>
        <h1>Organization workspace</h1>
      </section>
      <OrganizationManager initialOrganizationId={organizationId} />
    </main>
  );
}
