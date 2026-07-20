"use client";

import { FormEvent, useState } from "react";

import { runStrategySimulation } from "@/lib/api";
import type { SimulationRequest, SimulationResponse } from "@/lib/types";

const coreFields = [
  { key: "implied_apy", label: "Implied APY (%)" },
  { key: "borrow_apy", label: "Borrow APY (%)" },
  { key: "incentive_apy", label: "Incentive APY (%)" },
  { key: "ltv", label: "LTV (%)" },
  { key: "lltv", label: "LLTV (%)" },
  { key: "liquidity_usd", label: "Liquidity (USD)" },
  { key: "pt_price", label: "PT Price" }
] as const;

const advancedFields = [
  { key: "supply_apy", label: "Supply APY (%)" },
  { key: "collateral_value_usd", label: "Collateral Value (USD)" },
  { key: "debt_value_usd", label: "Debt Value (USD)" },
  { key: "borrow_apy_shock_multiplier", label: "Borrow Shock Multiplier" },
  { key: "liquidity_shock_pct", label: "Liquidity Shock (%)" },
  { key: "collateral_drawdown_pct", label: "Collateral Drawdown (%)" },
  { key: "early_exit_discount_pct", label: "Early Exit Discount (%)" },
  { key: "slippage_bps", label: "Slippage (BPS)" }
] as const;

const percentageKeys = new Set([
  "implied_apy",
  "supply_apy",
  "incentive_apy",
  "borrow_apy",
  "ltv",
  "lltv",
  "liquidity_shock_pct",
  "collateral_drawdown_pct",
  "early_exit_discount_pct"
]);

export function SimulationPanel() {
  const [strategyDescription, setStrategyDescription] = useState(
    "Pendle PT strategy using Morpho borrow"
  );
  const [protocols, setProtocols] = useState("pendle, morpho");
  const [maturityDate, setMaturityDate] = useState("");
  const [inputs, setInputs] = useState<Record<string, string>>({
    implied_apy: "12",
    borrow_apy: "5",
    incentive_apy: "1",
    ltv: "50",
    lltv: "86",
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
        .map(([key, value]) => [
          key,
          percentageKeys.has(key) ? Number(value) / 100 : Number(value)
        ])
    );
    return {
      ...numericPayload,
      strategy_description: strategyDescription,
      protocols: protocols
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
        .slice(0, 10),
      maturity_date: maturityDate || undefined
    };
  }

  function updateInput(key: string, value: string) {
    setInputs((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="stack">
      <form className="form-panel" onSubmit={handleSubmit}>
        <label>
          Strategy description
          <textarea
            maxLength={5000}
            onChange={(event) => setStrategyDescription(event.target.value)}
            rows={4}
            value={strategyDescription}
          />
        </label>
        <label>
          Protocols
          <input
            maxLength={255}
            onChange={(event) => setProtocols(event.target.value)}
            value={protocols}
          />
          <span className="field-help">Comma-separated, maximum 10 protocols.</span>
        </label>
        <fieldset>
          <legend>Core assumptions</legend>
          <p className="field-help">Percentage fields use normal units: 12 means 12%.</p>
          <div className="manual-grid">
            {coreFields.map((field) => (
              <SimulationInput field={field} inputs={inputs} key={field.key} onChange={updateInput} />
            ))}
          </div>
        </fieldset>
        <details className="advanced-fields">
          <summary>Advanced stress controls</summary>
          <div className="manual-grid advanced-grid">
            {advancedFields.map((field) => (
              <SimulationInput field={field} inputs={inputs} key={field.key} onChange={updateInput} />
            ))}
          </div>
        </details>
        <label>
          Maturity Date
          <input
            onChange={(event) => setMaturityDate(event.target.value)}
            type="date"
            value={maturityDate}
          />
        </label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <button className="primary-action" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Running stress scenarios..." : "Run Simulation"}
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
                <details>
                  <summary>Calculation details</summary>
                  <code>{scenario.formula}</code>
                </details>
                <ul className="compact-list">
                  {Object.entries(scenario.result).map(([key, value]) => (
                    <li key={key}>
                      <strong>{humanize(key)}:</strong> {formatResult(key, value)}
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

type SimulationField = (typeof coreFields | typeof advancedFields)[number];

function SimulationInput({
  field,
  inputs,
  onChange
}: {
  field: SimulationField;
  inputs: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <label>
      {field.label}
      <input
        inputMode="decimal"
        min="0"
        onChange={(event) => onChange(field.key, event.target.value)}
        placeholder="Optional"
        step="any"
        type="number"
        value={inputs[field.key] ?? ""}
      />
    </label>
  );
}

function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatResult(key: string, value: number | string | null): string {
  if (value === null) {
    return "Unknown";
  }
  if (typeof value !== "number") {
    return String(value);
  }
  if (key.includes("apy") || key.includes("pct") || key.includes("ltv") || key.includes("health_factor_change")) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (key.includes("usd") || key.includes("value") || key.includes("liquidity")) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2
    }).format(value);
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}
