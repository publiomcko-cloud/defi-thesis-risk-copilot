# Demo Script — DeFi Thesis & Risk Copilot

## 1. Demo Goal

The demo should show that the project is more than a generic crypto chatbot.

It should demonstrate a complete workflow:

```text
strategy prompt -> RAG retrieval -> data summary -> risk scoring -> structured report
```

## 2. Demo Setup

Use a synthetic strategy example.

No wallet connection, real funds, or transaction execution should be shown.

## 3. Demo Prompt

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

## 4. Demo Flow

### Step 1 — Open the home page

Explain:

- the tool is a DeFi research and risk copilot
- it does not execute trades
- it focuses on research, assumptions, and risk

### Step 2 — Submit a strategy

Paste the demo prompt into the strategy input form.

### Step 3 — Show source retrieval

Show the retrieved protocol documentation chunks.

Highlight:

- Pendle context
- Morpho lending context
- Aave or general liquidation context if relevant
- Chainlink or oracle context if included

### Step 4 — Show market data summary

Show available data and missing fields.

Explain that the system marks missing data instead of pretending to know everything.

### Step 5 — Show risk rating

Highlight:

- liquidity risk
- oracle risk
- borrow rate risk
- liquidation risk
- maturity risk
- composability risk

### Step 6 — Show final report

Show the report sections:

1. Executive summary
2. Strategy mechanics
3. Yield source
4. Assumptions
5. Risk analysis
6. Stress scenarios
7. Exit plan
8. Monitoring checklist
9. Sources
10. Disclaimer

### Step 7 — Export Markdown

Show that the report can be copied or exported as Markdown.

### Step 8 — Show repository

Briefly show:

- README
- architecture document
- RAG design
- agent design
- risk framework
- testing plan

## 5. Suggested Demo Video Length

Target length:

```text
2-4 minutes
```

## 6. Demo Success Criteria

The demo is successful if viewers understand:

- what problem the project solves
- how AI is used
- how RAG is used
- how agents are used
- how DeFi risk is structured
- why the project is safer than a trading bot
- how the architecture can evolve into a real product
