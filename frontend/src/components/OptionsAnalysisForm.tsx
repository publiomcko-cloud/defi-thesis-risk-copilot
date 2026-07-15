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
  const [impliedVolatility, setImpliedVolatility] = useState("75");
  const [bid, setBid] = useState("145");
  const [ask, setAsk] = useState("155");
  const [contracts, setContracts] = useState("1");
  const [expirationDate, setExpirationDate] = useState("");
  const [scenarioPrices, setScenarioPrices] = useState("2800, 3200, 3500");
  const [volatilityThesis, setVolatilityThesis] = useState(
    "Compare implied volatility with the expected realized volatility over the holding period."
  );
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
        implied_volatility: optionalPercent(impliedVolatility),
        bid: optionalNumber(bid),
        ask: optionalNumber(ask),
        contracts: Number(contracts),
        expiration_date: expirationDate || undefined,
        scenario_prices: scenarioPrices
          .split(",")
          .map((item) => Number(item.trim()))
          .filter((item) => Number.isFinite(item))
          .slice(0, 100),
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
          <legend>Position</legend>
          <div className="segmented-control">
            {(["call", "put"] as OptionType[]).map((type) => (
              <button
                aria-pressed={optionType === type}
                className={optionType === type ? "selected" : undefined}
                key={type}
                onClick={() => setOptionType(type)}
                type="button"
              >
                Long {type}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="manual-grid">
          <label>
            Asset
            <input maxLength={32} onChange={(event) => setAsset(event.target.value)} value={asset} />
          </label>
          <NumberInput label="Underlying price" setValue={setUnderlyingPrice} value={underlyingPrice} />
          <NumberInput label="Strike price" setValue={setStrikePrice} value={strikePrice} />
          <NumberInput label="Premium per contract" setValue={setPremium} value={premium} />
          <NumberInput label="Implied volatility (%)" setValue={setImpliedVolatility} value={impliedVolatility} />
          <NumberInput label="Bid" setValue={setBid} value={bid} />
          <NumberInput label="Ask" setValue={setAsk} value={ask} />
          <NumberInput label="Contracts" setValue={setContracts} value={contracts} />
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
          Scenario prices
          <input
            onChange={(event) => setScenarioPrices(event.target.value)}
            value={scenarioPrices}
          />
          <span className="field-help">Comma-separated underlying prices, up to 100 scenarios.</span>
        </label>
        <label>
          Volatility thesis
          <textarea
            maxLength={2000}
            onChange={(event) => setVolatilityThesis(event.target.value)}
            rows={3}
            value={volatilityThesis}
          />
        </label>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <button className="primary-action" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Analyzing payoff scenarios..." : "Analyze Option"}
        </button>
      </form>

      {result ? (
        <section className="panel">
          <p className="eyebrow">Long {result.option_type} on {result.underlying_asset}</p>
          <h2>Options Analysis</h2>
          <div className="metric-grid">
            <div className="metric">
              <span>Breakeven</span>
              <strong>{formatMoney(result.breakeven_price)}</strong>
            </div>
            <div className="metric">
              <span>Maximum loss</span>
              <strong>{formatMoney(result.max_loss)}</strong>
            </div>
            <div className="metric">
              <span>Maximum profit</span>
              <strong>{result.max_profit}</strong>
            </div>
            <div className="metric">
              <span>Bid/ask spread</span>
              <strong>
                {result.bid_ask_spread_pct == null
                  ? "Unavailable"
                  : `${result.bid_ask_spread_pct.toFixed(2)}%`}
              </strong>
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
        min="0"
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

function optionalPercent(value: string): number | undefined {
  const number = optionalNumber(value);
  return number === undefined ? undefined : number / 100;
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(value);
}
