import { DisclaimerBox } from "@/components/DisclaimerBox";
import { StrategyInputForm } from "@/components/StrategyInputForm";

const publicDemoMode = process.env.NEXT_PUBLIC_PUBLIC_DEMO_MODE === "true";

export default function AnalyzePage() {
  return (
    <main className="page narrow-page">
      <section className="page-heading">
        <p className="eyebrow">Strategy input</p>
        <h1>Analyze a DeFi Strategy</h1>
        <p>
          Submit a synthetic or read-only strategy prompt. The backend runs curated
          retrieval, market-data adapters, deterministic risk scoring, and structured
          report generation.
        </p>
      </section>

      {publicDemoMode ? (
        <section className="notice">
          <h2>Shared public environment</h2>
          <p>
            Inputs and generated reports may be stored in the shared demo database.
            Do not submit wallet addresses, private positions, credentials,
            confidential research, or personally identifying information.
          </p>
        </section>
      ) : null}

      <StrategyInputForm />
      <DisclaimerBox />
    </main>
  );
}
