import { Suspense } from "react";

import { InvitationAcceptance } from "@/components/InvitationAcceptance";

export default function OrganizationInvitationAcceptancePage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Organization</p>
        <h1>Accept invitation</h1>
        <p>Join an organization with the invitation token shared with you.</p>
      </section>
      <Suspense fallback={<section className="panel loading-panel">Loading invitation...</section>}>
        <InvitationAcceptance />
      </Suspense>
    </main>
  );
}
