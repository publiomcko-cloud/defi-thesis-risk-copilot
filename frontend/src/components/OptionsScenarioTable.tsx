import type { OptionScenario } from "@/lib/types";

type OptionsScenarioTableProps = {
  scenarios: OptionScenario[];
};

export function OptionsScenarioTable({ scenarios }: OptionsScenarioTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Underlying</th>
            <th>Intrinsic</th>
            <th>Payoff</th>
            <th>Return/Premium</th>
            <th>Moneyness</th>
          </tr>
        </thead>
        <tbody>
          {scenarios.map((scenario) => (
            <tr key={scenario.underlying_price}>
              <td>{scenario.underlying_price}</td>
              <td>{scenario.intrinsic_value}</td>
              <td>{scenario.payoff}</td>
              <td>
                {scenario.return_on_premium_pct === null ||
                scenario.return_on_premium_pct === undefined
                  ? "n/a"
                  : `${(scenario.return_on_premium_pct * 100).toFixed(1)}%`}
              </td>
              <td>{scenario.moneyness}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
