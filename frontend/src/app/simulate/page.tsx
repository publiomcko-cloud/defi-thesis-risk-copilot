import { DisclaimerBox } from "@/components/DisclaimerBox";
import { SimulationPanel } from "@/components/SimulationPanel";

export default function SimulatePage() {
  return (
    <main className="page">
      <section className="page-heading">
        <p className="eyebrow">Deterministic scenarios</p>
        <h1>Strategy Simulator</h1>
        <p>
          Run transparent stress scenarios for spread, borrow cost, liquidity,
          collateral drawdown, early exit, incentives, and combined adverse
          assumptions.
        </p>
      </section>

      <SimulationPanel />
      <DisclaimerBox text="Simulation outputs are deterministic educational scenarios. They are not forecasts, guarantees, recommendations, or instructions to enter or exit a position." />
    </main>
  );
}
