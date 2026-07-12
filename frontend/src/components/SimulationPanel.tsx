"use client";

import { FormEvent, useState } from "react";

import { runStrategySimulation } from "@/lib/api";
import type { SimulationRequest, SimulationResponse } from "@/lib/types";

const numericFields = [
  { key: "implied_apy", label: "Implied APY" },
  { key: "supply_apy", label: "Supply APY" },
  { key: "incentive_apy", label: "Incentive APY" },
  { key: "borrow_apy", label: "Borrow APY" },
  { key: "ltv", label: "LTV" },
  { key: "lltv", label: "LLTV" },
  { key: "collateral_value_usd", label: "Collateral Value USD" },
  { key: "debt_value_usd", label: "Debt Value USD" },
  { key: "liquidity_usd", label: "Liquidity USD" },
  { key: "pt_price", label: "PT Price" },
  { key: "borrow_apy_shock_multiplier", label: "Borrow Shock Multiplier" },
  { key: "liquidity_shock_pct", label: "Liquidity Shock %" },
  { key: "collateral_drawdown_pct", label: "Collateral Drawdown %" },
  { key: "early_exit_discount_pct", label: "Early Exit Discount %" },
  { key: "slippage_bps", label: "Slippage BPS" }
] as const;

export function SimulationPanel() {
  const [strategyDescription, setStrategyDescription] = useState(
    "Pendle PT strategy using Morpho borrow"
  );
  const [protocols, setProtocols] = useState("pendle,morpho");
  const [maturityDate, setMaturityDate] = useState("");
  const [inputs, setInputs] = useState<Record<string, string>>({
    implied_apy: "0.12",
    borrow_apy: "0.05",
    incentive_apy: "0.01",
    ltv: "0.5",
    lltv: "0.86",
    liquidity_usd: "1000000",
    pt_price: "0.95",
    slippage_bps: "30"
  });
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await runStrategySimulation(buildPayload());
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Simulation failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function buildPayload(): SimulationRequest {
    const numericPayload = Object.fromEntries(
      Object.entries(inputs)
        .filter(([, value]) => value.trim() !== "")
        .map(([key, value]) => [key, Number(value)])
    );
    return {
      ...numericPayload,
      strategy_description: strategyDescription,
      protocols: protocols
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      maturity_date: maturityDate || undefined
    };
  }

  return (
    <div className="stack">
      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          Strategy description
          <textarea
            onChange={(event) => setStrategyDescription(event.target.value)}
            rows={4}
            value={strategyDescription}
          />
        </label>
        <label>
          Protocols
          <input
            onChange={(event) => setProtocols(event.target.value)}
            value={protocols}
          />
        </label>
        <div className="manual-grid">
          {numericFields.map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                inputMode="decimal"
                onChange={(event) =>
                  setInputs((current) => ({
                    ...current,
                    [field.key]: event.target.value
                  }))
                }
                placeholder="Optional"
                step="any"
                type="number"
                value={inputs[field.key] ?? ""}
              />
            </label>
          ))}
        </div>
        <label>
          Maturity Date
          <input
            onChange={(event) => setMaturityDate(event.target.value)}
            type="date"
            value={maturityDate}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button className="primary-action" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Simulating..." : "Run Simulation"}
        </button>
      </form>

      {result ? (
        <section className="panel">
          <p className="eyebrow">Simulation status: {result.status}</p>
          <h2>Scenario Results</h2>
          {result.missing_data.length > 0 ? (
            <p>Missing data: {result.missing_data.join(", ")}</p>
          ) : null}
          <div className="scenario-grid">
            {result.scenarios.map((scenario) => (
              <article className="scenario-card" key={scenario.scenario_type}>
                <h3>{scenario.name}</h3>
                <p>{scenario.interpretation}</p>
                <code>{scenario.formula}</code>
                <ul>
                  {Object.entries(scenario.result).map(([key, value]) => (
                    <li key={key}>
                      {key}: {value === null ? "unknown" : String(value)}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
          <p>{result.disclaimer}</p>
        </section>
      ) : null}
    </div>
  );
}
