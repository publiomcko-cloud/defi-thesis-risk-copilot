import { DisclaimerBox } from "@/components/DisclaimerBox";
import { OptionsAnalysisForm } from "@/components/OptionsAnalysisForm";

export default function OptionsPage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Options and volatility</p>
        <h1>Options Analysis</h1>
        <p>
          Analyze manually entered crypto option parameters with deterministic
          payoff scenarios, breakeven, premium risk, spread risk, and
          volatility framing.
        </p>
      </section>

      <OptionsAnalysisForm />
      <DisclaimerBox text="Options analysis is educational and scenario-based. It does not recommend buying or selling options and does not guarantee payoff, liquidity, or volatility outcomes." />
    </main>
  );
}
