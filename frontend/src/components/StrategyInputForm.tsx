"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { analyzeStrategy } from "@/lib/api";
import type { ManualInputs } from "@/lib/types";

const demoPrompt =
  "Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.";

const protocolOptions = ["pendle", "morpho", "aave"];

const basicManualFields = [
  { key: "borrow_apy", label: "Borrow APY (%)", type: "number", placeholder: "5" },
  { key: "implied_apy", label: "Implied APY (%)", type: "number", placeholder: "12" },
  { key: "liquidity_usd", label: "Liquidity (USD)", type: "number", placeholder: "1000000" },
  { key: "ltv", label: "LTV (%)", type: "number", placeholder: "50" },
  { key: "lltv", label: "LLTV (%)", type: "number", placeholder: "86" }
] as const;

const advancedManualFields = [
  { key: "collateral_asset", label: "Collateral Asset", type: "text", placeholder: "ETH" },
  { key: "debt_asset", label: "Debt Asset", type: "text", placeholder: "USDC" },
  { key: "pt_price", label: "PT Price", type: "number", placeholder: "0.95" },
  { key: "maturity_date", label: "Maturity Date", type: "date", placeholder: "" },
  { key: "token_id", label: "Token ID", type: "text", placeholder: "ethereum" },
  { key: "supply_apy", label: "Supply APY (%)", type: "number", placeholder: "4" },
  {
    key: "liquidation_threshold",
    label: "Liquidation Threshold (%)",
    type: "number",
    placeholder: "82"
  },
  { key: "reserve_asset", label: "Reserve Asset", type: "text", placeholder: "USDC" }
] as const;

const percentageKeys = new Set([
  "borrow_apy",
  "implied_apy",
  "ltv",
  "lltv",
  "supply_apy",
  "liquidation_threshold"
]);

const numericManualInputKeys = new Set<string>(
  [...basicManualFields, ...advancedManualFields]
    .filter((field) => field.type === "number")
    .map((field) => field.key)
);

export function StrategyInputForm() {
  const router = useRouter();
  const [strategyDescription, setStrategyDescription] = useState(demoPrompt);
  const [selectedProtocols, setSelectedProtocols] = useState<string[]>([
    "pendle",
    "morpho"
  ]);
  const [marketUrl, setMarketUrl] = useState("");
  const [manualInputs, setManualInputs] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (selectedProtocols.length === 0) {
      setError("Select at least one protocol before running the analysis.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await analyzeStrategy({
        strategy_description: strategyDescription,
        protocols: selectedProtocols,
        market_url: marketUrl || null,
        manual_inputs: normalizeManualInputs(manualInputs),
        analysis_depth: "standard"
      });
      router.push(`/reports/${response.report_id}`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The analysis request failed. The free-tier backend may still be waking up."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleProtocol(protocol: string) {
    setSelectedProtocols((current) =>
      current.includes(protocol)
        ? current.filter((item) => item !== protocol)
        : [...current, protocol]
    );
  }

  function updateManualInput(key: string, value: string) {
    setManualInputs((current) => ({
      ...current,
      [key]: value
    }));
  }

  function resetExample() {
    setStrategyDescription(demoPrompt);
    setSelectedProtocols(["pendle", "morpho"]);
    setMarketUrl("");
    setManualInputs({});
    setError(null);
  }

  return (
    <form className="form-panel" onSubmit={handleSubmit}>
      <div className="section-toolbar">
        <div>
          <h2>Strategy thesis</h2>
          <p>Start with the example or describe another synthetic/read-only strategy.</p>
        </div>
        <button className="secondary-action" onClick={resetExample} type="button">
          Load example
        </button>
      </div>

      <label>
        Strategy description
        <textarea
          maxLength={5000}
          value={strategyDescription}
          onChange={(event) => setStrategyDescription(event.target.value)}
          rows={8}
          minLength={10}
          required
        />
        <span className="field-help">{strategyDescription.length}/5000 characters</span>
      </label>

      <fieldset>
        <legend>Protocols</legend>
        <div className="segmented-control">
          {protocolOptions.map((protocol) => (
            <button
              aria-pressed={selectedProtocols.includes(protocol)}
              className={selectedProtocols.includes(protocol) ? "selected" : undefined}
              key={protocol}
              onClick={() => toggleProtocol(protocol)}
              type="button"
            >
              {protocol}
            </button>
          ))}
        </div>
      </fieldset>

      <label>
        Market URL
        <input
          maxLength={2048}
          onChange={(event) => setMarketUrl(event.target.value)}
          placeholder="Optional protocol market URL"
          type="url"
          value={marketUrl}
        />
      </label>

      <fieldset>
        <legend>Core assumptions</legend>
        <p className="field-help">Enter percentages as normal values: 5 means 5%, not 500%.</p>
        <div className="manual-grid">
          {basicManualFields.map((field) => (
            <ManualInputField
              field={field}
              key={field.key}
              onChange={updateManualInput}
              value={manualInputs[field.key] ?? ""}
            />
          ))}
        </div>
      </fieldset>

      <details className="advanced-fields">
        <summary>Advanced assumptions</summary>
        <div className="manual-grid advanced-grid">
          {advancedManualFields.map((field) => (
            <ManualInputField
              field={field}
              key={field.key}
              onChange={updateManualInput}
              value={manualInputs[field.key] ?? ""}
            />
          ))}
        </div>
      </details>

      {error ? <p className="error" role="alert">{error}</p> : null}

      <button className="primary-action" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Analyzing and building report..." : "Analyze Strategy"}
      </button>
    </form>
  );
}

function normalizeManualInputs(inputs: Record<string, string>): ManualInputs {
  return Object.fromEntries(
    Object.entries(inputs)
      .filter(([, value]) => value.trim() !== "")
      .map(([key, value]) => {
        if (!numericManualInputKeys.has(key)) {
          return [key, value.trim()];
        }
        const numericValue = Number(value);
        return [key, percentageKeys.has(key) ? numericValue / 100 : numericValue];
      })
  ) as ManualInputs;
}

type ManualField = (typeof basicManualFields | typeof advancedManualFields)[number];

type ManualInputFieldProps = {
  field: ManualField;
  onChange: (key: string, value: string) => void;
  value: string;
};

function ManualInputField({ field, onChange, value }: ManualInputFieldProps) {
  return (
    <label>
      {field.label}
      <input
        inputMode={field.type === "number" ? "decimal" : undefined}
        max={field.type === "number" && percentageKeys.has(field.key) ? 1000 : undefined}
        min={field.type === "number" ? 0 : undefined}
        onChange={(event) => onChange(field.key, event.target.value)}
        placeholder={field.placeholder || "Optional"}
        type={field.type}
        step={field.type === "number" ? "any" : undefined}
        value={value}
      />
    </label>
  );
}
