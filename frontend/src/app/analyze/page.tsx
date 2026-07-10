import { StrategyInputForm } from "@/components/StrategyInputForm";
import { DisclaimerBox } from "@/components/DisclaimerBox";

export default function AnalyzePage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Strategy input</p>
        <h1>Analyze a DeFi Strategy</h1>
        <p>
          Submit a synthetic or read-only strategy prompt. Phase 3 calls the
          mocked backend API and prepares the flow for later RAG, market data,
          risk scoring, and report generation.
        </p>
      </section>

      <StrategyInputForm />
      <DisclaimerBox />
    </main>
  );
}
