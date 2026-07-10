# Data Sources — DeFi Thesis & Risk Copilot

## 1. Data Source Strategy

The MVP should avoid mandatory paid APIs.

The first version should use:

- official protocol documentation
- public APIs
- free tiers
- cached data
- manual fallback fields

The system should clearly mark missing, estimated, cached, or user-provided data.

## 2. MVP Sources

### 2.1 Protocol Documentation

Primary use:

- RAG
- protocol explanation
- mechanism verification
- risk terminology
- source citations

Initial documentation sources:

- Pendle documentation
- Morpho documentation
- Aave documentation
- Chainlink documentation
- internal DeFi risk notes

### 2.2 DefiLlama

Primary use:

- TVL
- protocol categories
- yields
- protocol metadata

### 2.3 CoinGecko

Primary use:

- token prices
- market cap
- volume
- historical market data when available

### 2.4 Morpho API

Primary use:

- markets
- vaults
- collateral asset
- loan asset
- LLTV
- APY
- utilization
- oracle information when available

### 2.5 Aave API or Subgraphs

Primary use:

- reserve data
- supply rates
- borrow rates
- collateral parameters
- liquidation thresholds
- Health Factor concepts for position analysis

### 2.6 Manual Data Input

Manual input is important for MVP reliability.

Examples:

- PT price
- implied APY
- maturity date
- borrow APY
- collateral amount
- debt amount
- LTV target
- estimated slippage
- pool liquidity

## 3. Future Sources

Future data sources:

- Dune API
- The Graph subgraphs
- Chainlink price feeds
- Pendle market APIs
- Token Terminal
- Messari
- Nansen
- Arkham
- governance forums
- protocol risk dashboards
- audit reports
- social and narrative sources

## 4. Data Adapter Design

Each source should use an adapter pattern.

```text
data_sources/
├── base.py
├── coingecko.py
├── defillama.py
├── morpho.py
├── aave.py
├── pendle.py
├── dune.py
├── thegraph.py
└── manual.py
```

Each adapter should support:

1. live fetch
2. cache read
3. error handling
4. normalized output
5. source metadata

## 5. Fallback Logic

Preferred flow:

```text
Try live API
    -> if unavailable, use cache
    -> if cache is missing, ask for manual input
    -> if still missing, mark as unknown in the report
```

## 6. Data Quality Rules

The system should track:

- source name
- fetch timestamp
- data freshness
- confidence level
- missing fields
- manual overrides
- assumptions

## 7. Paid API Policy

Paid APIs should not be required for the MVP.

Premium providers may be added as optional future adapters.
