import { DisclaimerBox } from "@/components/DisclaimerBox";

export default function AboutPage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Portfolio project</p>
        <h1>About This Copilot</h1>
        <p>
          DeFi Thesis & Risk Copilot is designed to demonstrate applied AI
          engineering for DeFi research: typed APIs, source-grounded analysis,
          market data normalization, rule-based risk scoring, and structured
          report generation.
        </p>
      </section>

      <section className="panel">
        <h2>Current Phase</h2>
        <p>
          The frontend flow is usable against the controlled backend workflow:
          persisted reports, curated local RAG retrieval, market adapters,
          deterministic scoring, structured reports, and Markdown export. LLM
          report writing and production deployment remain later phases.
        </p>
      </section>

      <DisclaimerBox />
    </main>
  );
}
