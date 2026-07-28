"use client";

import { KnowledgeWorkspace } from "@/components/KnowledgeWorkspace";
import { PublicAdminBoundary } from "@/components/PublicAdminBoundary";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function KnowledgePage() {
  if (publicDemoMode) {
    return (
      <PublicAdminBoundary
        title="Knowledge management is private"
        description="Private and organization knowledge documents are available only in an authenticated deployment. The public demo continues to use its curated rollback corpus."
      />
    );
  }
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Durable knowledge</p>
        <h1>Knowledge Workspace</h1>
        <p>Manage source ownership, immutable document versions, worker ingestion, embeddings, and safe recovery without exposing private objects.</p>
      </section>
      <KnowledgeWorkspace />
    </main>
  );
}
