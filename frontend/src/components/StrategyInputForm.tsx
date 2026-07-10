"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { analyzeStrategy } from "@/lib/api";
import type { ManualInputs } from "@/lib/types";

const demoPrompt =
  "Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.";

const protocolOptions = ["pendle", "morpho", "aave"];

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
          {[
            ["borrow_apy", "Borrow APY"],
            ["implied_apy", "Implied APY"],
            ["liquidity_usd", "Liquidity USD"],
            ["ltv", "LTV"],
            ["lltv", "LLTV"]
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                inputMode="decimal"
                onChange={(event) => updateManualInput(key, event.target.value)}
                placeholder="Optional"
                type="number"
                step="any"
                value={manualInputs[key] ?? ""}
              />
            </label>
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
      .map(([key, value]) => [key, Number(value)])
  ) as ManualInputs;
}
