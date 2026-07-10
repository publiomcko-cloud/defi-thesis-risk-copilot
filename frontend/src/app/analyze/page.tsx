import { StrategyInputForm } from "@/components/StrategyInputForm";
import { DisclaimerBox } from "@/components/DisclaimerBox";

export default function AnalyzePage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Strategy input</p>
        <h1>Analyze a DeFi Strategy</h1>
        <p>
          Submit a synthetic or read-only strategy prompt. The backend runs the
          controlled local workflow with curated RAG retrieval, market data
          adapters, deterministic risk scoring, and structured report generation.
        </p>
      </section>

      <StrategyInputForm />
      <DisclaimerBox />
    </main>
  );
}
