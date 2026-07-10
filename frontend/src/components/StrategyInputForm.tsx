"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { analyzeStrategy } from "@/lib/api";
import type { ManualInputs } from "@/lib/types";

const demoPrompt =
  "Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.";

const protocolOptions = ["pendle", "morpho", "aave"];

const basicManualFields = [
  { key: "borrow_apy", label: "Borrow APY", type: "number" },
  { key: "implied_apy", label: "Implied APY", type: "number" },
  { key: "liquidity_usd", label: "Liquidity USD", type: "number" },
  { key: "ltv", label: "LTV", type: "number" },
  { key: "lltv", label: "LLTV", type: "number" }
] as const;

const advancedManualFields = [
  { key: "collateral_asset", label: "Collateral Asset", type: "text" },
  { key: "debt_asset", label: "Debt Asset", type: "text" },
  { key: "pt_price", label: "PT Price", type: "number" },
  { key: "maturity_date", label: "Maturity Date", type: "date" },
  { key: "token_id", label: "Token ID", type: "text" },
  { key: "supply_apy", label: "Supply APY", type: "number" },
  {
    key: "liquidation_threshold",
    label: "Liquidation Threshold",
    type: "number"
  },
  { key: "reserve_asset", label: "Reserve Asset", type: "text" }
] as const;

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
    setIsSubmitting(true);
    setError(null);

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
          : "The analysis request failed."
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

  return (
    <form className="form-panel" onSubmit={handleSubmit}>
      <label>
        Strategy description
        <textarea
          value={strategyDescription}
          onChange={(event) => setStrategyDescription(event.target.value)}
          rows={8}
          minLength={10}
          required
        />
      </label>

      <fieldset>
        <legend>Protocols</legend>
        <div className="segmented-control">
          {protocolOptions.map((protocol) => (
            <button
              aria-pressed={selectedProtocols.includes(protocol)}
              className={
                selectedProtocols.includes(protocol) ? "selected" : undefined
              }
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
          onChange={(event) => setMarketUrl(event.target.value)}
          placeholder="Optional protocol market URL"
          type="url"
          value={marketUrl}
        />
      </label>

      <fieldset>
        <legend>Manual Inputs</legend>
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

      <fieldset>
        <legend>Advanced Manual Inputs</legend>
        <div className="manual-grid">
          {advancedManualFields.map((field) => (
            <ManualInputField
              field={field}
              key={field.key}
              onChange={updateManualInput}
              value={manualInputs[field.key] ?? ""}
            />
          ))}
        </div>
      </fieldset>

      {error ? <p className="error">{error}</p> : null}

      <button className="primary-action" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Analyzing..." : "Analyze Strategy"}
      </button>
    </form>
  );
}

function normalizeManualInputs(inputs: Record<string, string>): ManualInputs {
  return Object.fromEntries(
    Object.entries(inputs)
      .filter(([, value]) => value.trim() !== "")
      .map(([key, value]) => [
        key,
        numericManualInputKeys.has(key) ? Number(value) : value.trim()
      ])
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
        onChange={(event) => onChange(field.key, event.target.value)}
        placeholder="Optional"
        type={field.type}
        step={field.type === "number" ? "any" : undefined}
        value={value}
      />
    </label>
  );
}
