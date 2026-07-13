"use client";

import { FormEvent, useState } from "react";

import { analyzeOption } from "@/lib/api";
import type { OptionType, OptionsAnalysisResponse } from "@/lib/types";
import { OptionsScenarioTable } from "./OptionsScenarioTable";

export function OptionsAnalysisForm() {
  const [optionType, setOptionType] = useState<OptionType>("call");
  const [asset, setAsset] = useState("ETH");
  const [underlyingPrice, setUnderlyingPrice] = useState("3000");
  const [strikePrice, setStrikePrice] = useState("3200");
  const [premium, setPremium] = useState("150");
  const [impliedVolatility, setImpliedVolatility] = useState("0.75");
  const [bid, setBid] = useState("145");
  const [ask, setAsk] = useState("155");
  const [expirationDate, setExpirationDate] = useState("");
  const [scenarioPrices, setScenarioPrices] = useState("2800,3200,3500");
  const [volatilityThesis, setVolatilityThesis] = useState("Compare implied volatility against the user's expected realized volatility.");
  const [result, setResult] = useState<OptionsAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await analyzeOption({
        option_type: optionType,
        underlying_asset: asset,
        underlying_price: Number(underlyingPrice),
        strike_price: Number(strikePrice),
        premium: Number(premium),
        implied_volatility: optionalNumber(impliedVolatility),
        bid: optionalNumber(bid),
        ask: optionalNumber(ask),
        expiration_date: expirationDate || undefined,
        scenario_prices: scenarioPrices
          .split(",")
          .map((item) => Number(item.trim()))
          .filter((item) => Number.isFinite(item)),
        volatility_thesis: volatilityThesis || undefined
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Options analysis failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="stack">
      <form className="form-panel" onSubmit={handleSubmit}>
        <fieldset>
          <legend>Option Type</legend>
          <div className="segmented-control">
            {(["call", "put"] as OptionType[]).map((type) => (
              <button
                aria-pressed={optionType === type}
                className={optionType === type ? "selected" : undefined}
                key={type}
                onClick={() => setOptionType(type)}
                type="button"
              >
                {type}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="manual-grid">
          <label>
            Asset
            <input onChange={(event) => setAsset(event.target.value)} value={asset} />
          </label>
          <NumberInput label="Underlying Price" setValue={setUnderlyingPrice} value={underlyingPrice} />
          <NumberInput label="Strike Price" setValue={setStrikePrice} value={strikePrice} />
          <NumberInput label="Premium" setValue={setPremium} value={premium} />
          <NumberInput label="Implied Volatility" setValue={setImpliedVolatility} value={impliedVolatility} />
          <NumberInput label="Bid" setValue={setBid} value={bid} />
          <NumberInput label="Ask" setValue={setAsk} value={ask} />
          <label>
            Expiration
            <input
              onChange={(event) => setExpirationDate(event.target.value)}
              type="date"
              value={expirationDate}
            />
          </label>
        </div>
        <label>
          Scenario Prices
          <input
            onChange={(event) => setScenarioPrices(event.target.value)}
            value={scenarioPrices}
          />
        </label>
        <label>
          Volatility Thesis
          <textarea
            onChange={(event) => setVolatilityThesis(event.target.value)}
            rows={3}
            value={volatilityThesis}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button className="primary-action" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Analyzing..." : "Analyze Option"}
        </button>
      </form>

      {result ? (
        <section className="panel">
          <p className="eyebrow">{result.option_type} option on {result.underlying_asset}</p>
          <h2>Options Analysis</h2>
          <div className="content-grid">
            <div>
              <h3>Breakeven</h3>
              <p>{result.breakeven_price}</p>
            </div>
            <div>
              <h3>Max Loss</h3>
              <p>{result.max_loss}</p>
            </div>
            <div>
              <h3>Max Profit</h3>
              <p>{result.max_profit}</p>
            </div>
          </div>
          <p>{result.volatility_summary}</p>
          {result.missing_data.length ? (
            <p>Missing data: {result.missing_data.join(", ")}</p>
          ) : null}
          <OptionsScenarioTable scenarios={result.scenarios} />
          <h3>Risks</h3>
          <ul>
            {result.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
          <p>{result.disclaimer}</p>
        </section>
      ) : null}
    </div>
  );
}

type NumberInputProps = {
  label: string;
  value: string;
  setValue: (value: string) => void;
};

function NumberInput({ label, value, setValue }: NumberInputProps) {
  return (
    <label>
      {label}
      <input
        inputMode="decimal"
        onChange={(event) => setValue(event.target.value)}
        step="any"
        type="number"
        value={value}
      />
    </label>
  );
}

function optionalNumber(value: string): number | undefined {
  if (value.trim() === "") {
    return undefined;
  }
  return Number(value);
}
