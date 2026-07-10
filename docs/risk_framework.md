# Risk Framework — DeFi Thesis & Risk Copilot

## 1. Purpose

The risk framework provides a repeatable structure for analyzing DeFi strategies.

The MVP risk framework is rule-based, explainable, and conservative.

It is not a guarantee of safety and must not be treated as investment advice.

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

## 5. Required Output

Every risk report should include:

- final risk rating
- score explanation
- main risk drivers
- missing data
- confidence level
- monitoring checklist
- scenario warnings

## 6. Future Improvements

Future phases may add:

- weighted scoring
- historical volatility input
- liquidity depth modeling
- borrow rate scenario simulation
- liquidation buffer calculation
- portfolio-level risk aggregation
- trained risk classifier using PyTorch and Hugging Face
