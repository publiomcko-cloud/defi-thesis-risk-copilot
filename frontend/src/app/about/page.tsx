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
          The frontend flow is now usable against mocked backend responses.
          RAG, live market adapters, deterministic scoring, persistence, and
          LLM report writing are intentionally deferred to later phases.
        </p>
      </section>

      <DisclaimerBox />
    </main>
  );
}
