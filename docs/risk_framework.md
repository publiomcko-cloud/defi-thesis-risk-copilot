# Risk Framework — DeFi Thesis & Risk Copilot

## 1. Purpose

The risk framework provides a repeatable structure for analyzing DeFi strategies.

The MVP risk framework is rule-based, explainable, and conservative.

It is not a guarantee of safety and must not be treated as investment advice.

After the Phase 10 MVP checkpoint, the framework expands to support strategy simulation, watchlist alert rules, options/volatility analysis, and future ML-assisted risk classification.

## 2. Risk Categories

### 2.1 Protocol Risk

Risk from smart contracts, governance, upgrades, protocol design, audits, or implementation bugs.

### 2.2 Market Risk

Risk from price changes in collateral assets, debt assets, underlying assets, or yield-bearing assets.

### 2.3 Liquidity Risk

Risk that the user cannot enter or exit a strategy without high slippage or delayed execution.

### 2.4 Oracle Risk

Risk from incorrect, delayed, manipulated, or unsuitable price feeds.

### 2.5 Liquidation Risk

Risk that a lending or leveraged position becomes liquidatable due to collateral movement, debt growth, borrow rate changes, or parameter changes.

### 2.6 Borrow Rate Risk

Risk that variable borrow APY rises and reduces or eliminates the net strategy spread.

### 2.7 Maturity Risk

Risk related to fixed-yield assets, PT maturity, secondary market liquidity, and exit before maturity.

### 2.8 Composability Risk

Risk from combining multiple protocols in one strategy.

### 2.9 Operational Risk

Risk from user mistakes, wrong chain, wrong asset, approvals, bridge issues, gas spikes, or misunderstanding of protocol mechanics.

### 2.10 Incentive Risk

Risk that yield depends heavily on temporary rewards or emissions.

### 2.11 Model and Data Risk

Risk that analysis quality is reduced by stale sources, incomplete data, incorrect assumptions, weak retrieval, or overreliance on model-generated text.

### 2.12 Volatility and Options Risk

Risk from option premium decay, implied volatility changes, strike selection, expiration timing, bid/ask spread, and non-linear payoff exposure.

## 3. MVP Risk Ratings

The MVP uses four risk levels:

1. Conservative
2. Moderate
3. Aggressive
4. Very Risky

## 4. Rule-Based Scoring

Example initial scoring:

```text
Base risk: 1

+1 if the strategy uses more than one protocol.
+1 if the strategy uses leverage.
+1 if collateral is volatile.
+1 if borrow APY is variable.
+1 if liquidity is low or unknown.
+1 if exit depends on a secondary market.
+1 if oracle risk is unclear.
+1 if maturity timing creates exit risk.
+1 if the strategy depends heavily on incentives.
+1 if documentation or data is incomplete.
```

Suggested mapping:

```text
0-2 points: Conservative
3-4 points: Moderate
5-6 points: Aggressive
7+ points: Very Risky
```

## 5. Required Report Output

Every risk report should include:

- final risk rating
- score explanation
- main risk drivers
- missing data
- confidence level
- monitoring checklist
- scenario warnings
- sources
- disclaimer

## 6. Strategy Simulation Framework

Post-MVP Phase 4 adds deterministic scenario outputs.

Initial simulations:

- net spread estimate
- borrow APY shock
- liquidity or slippage shock
- collateral drawdown
- LTV and liquidation buffer approximation
- early exit before maturity
- incentive removal
- combined adverse scenario

Simulation outputs must include:

- input assumptions
- formulas or calculation method
- missing fields
- scenario result
- risk interpretation
- non-advisory disclaimer

Current implementation:

- accepts explicit user inputs through `/api/simulation/run`
- returns deterministic scenario objects with formulas, assumptions, missing data, and interpretation
- adds a Simulation Summary section to generated reports
- exposes a frontend simulator at `/simulate`
- does not forecast probabilities, recommend trades, or guarantee outcomes

Simulation outputs must not include:

- buy/sell instructions
- position sizing instructions
- guaranteed outcomes

## 7. Watchlist and Alert Risk Rules

Watchlist alerts should be rule-based.

Initial rule types:

```text
borrow_apy_above_threshold
net_spread_below_threshold
liquidity_below_threshold
maturity_date_approaching
risk_score_changed
missing_data_resolved
new_discovered_item_needs_review
source_update_detected
```

Alert events should explain why they triggered and should not recommend a trade.

## 8. Options and Volatility Risk Rules

Options analysis should remain educational and scenario-based.

Initial option metrics:

- option type
- strike
- expiration
- premium
- breakeven
- maximum loss
- payoff at selected prices
- implied volatility
- bid/ask spread
- time to expiration

Options reports should explain:

- directional exposure
- volatility exposure
- time decay risk
- liquidity/spread risk
- maximum loss based on premium paid
- missing assumptions

Options reports must not say whether to buy or sell an option.

## 9. LLM and ML Risk Guardrails

Optional LLM synthesis may improve language quality, but it must not:

- replace deterministic risk scoring
- hide missing data
- remove sources
- remove disclaimers
- invent market values
- produce financial advice

Future ML classifiers may assist the risk engine, but deterministic scoring remains the authoritative MVP framework until a validated model is explicitly promoted.

## 10. Future Improvements

Future phases may add:

- weighted scoring
- historical volatility input
- liquidity depth modeling
- borrow rate scenario simulation
- liquidation buffer calculation
- portfolio-level risk aggregation
- options payoff modeling
- volatility scenario analysis
- alert rule calibration
- trained risk classifier using PyTorch and Hugging Face
