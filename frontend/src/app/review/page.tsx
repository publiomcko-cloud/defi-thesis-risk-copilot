import { DisclaimerBox } from "@/components/DisclaimerBox";
import { ReviewQueueTable } from "@/components/ReviewQueueTable";

export default function ReviewPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Human review</p>
        <h1>Evaluation Queue</h1>
        <p>
          Review monitored source candidates, run controlled evaluations, and
          explicitly mark whether an item should be prepared for later RAG
          ingestion.
        </p>
      </section>

      <ReviewQueueTable />
      <DisclaimerBox text="Approving a review item only prepares it for a future ingestion step. This screen does not ingest sources into RAG, execute actions, or approve trading decisions." />
    </main>
  );
}
