import { DisclaimerBox } from "@/components/DisclaimerBox";
import { ReviewQueueTable } from "@/components/ReviewQueueTable";

export default function ReviewPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Human review</p>
        <h1>Evaluation Queue</h1>
        <p>
          Review discovered source candidates, run controlled evaluations,
          approve eligible items, and explicitly ingest approved sources into
          local RAG.
        </p>
      </section>

      <ReviewQueueTable />
      <DisclaimerBox text="Approving a review item does not ingest it automatically. Only approved items can be explicitly ingested into local RAG. This screen does not execute trades or approve trading decisions." />
    </main>
  );
}
