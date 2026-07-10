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

After the Phase 10 MVP checkpoint, data-source work becomes an active product-expansion area. The next data-source phases should support source monitoring, discovered-item normalization, automated evaluation, human review, and optional RAG ingestion.

## 2. Current MVP Sources

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

### 2.4 Morpho API or Manual Fallback

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

### 2.6 Pendle Market Data or Manual Fallback

Primary use:

- PT price
- implied APY
- maturity date
- pool liquidity
- market URL
- underlying asset

### 2.7 Manual Data Input

Manual input is important for MVP reliability.

Examples:

- PT price
- implied APY
- maturity date
- borrow APY
- collateral amount
- debt amount
- collateral asset
- debt asset
- LTV target
- LLTV
- estimated slippage
- pool liquidity
- token ID

## 3. Active Post-MVP Source Categories

The next product phases should add source monitoring and discovered-item normalization.

### 3.1 Market Discovery Sources

Initial monitored sources:

- Pendle markets
- Morpho markets or vaults
- Aave reserves
- DefiLlama protocol and yield data
- CoinGecko token metadata

### 3.2 Governance and Documentation Sources

Initial monitored sources:

- protocol docs
- governance forums
- risk parameter proposals
- audit reports
- risk dashboards
- changelogs

### 3.3 Optional Premium Sources

Premium providers should remain optional:

- Token Terminal
- Messari
- Nansen
- Arkham
- Dune paid tiers

## 4. Data Adapter Design

Each source should use an adapter pattern.

Current and planned structure:

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
6. missing-field reporting
7. assumptions

## 5. Monitoring Source Design

Post-MVP monitoring should add a separate layer instead of overloading market data adapters.

Recommended structure:

```text
monitoring/
├── sources.py
├── collectors.py
├── normalizer.py
└── discovery_service.py
```

A discovered item should include:

```text
id
source
source_type
title
url
protocol
chain
asset
market_identifier
discovered_at
raw_payload
status
```

Default status:

```text
needs_review
```

## 6. Fallback Logic

Preferred flow:

```text
Try live API
    -> if unavailable, use cache
    -> if cache is missing, ask for manual input
    -> if still missing, mark as unknown in the report
```

For monitored sources:

```text
Collect source
    -> if unavailable, record failure
    -> if duplicate, update last_seen timestamp
    -> if new, create discovered item
    -> mark as needs_review
```

## 7. Data Quality Rules

The system should track:

- source name
- fetch timestamp
- data freshness
- confidence level
- missing fields
- manual overrides
- assumptions
- source quality
- review status
- duplicate detection
- raw payload reference

## 8. Automated Evaluation Input Rules

Discovered items can be evaluated automatically only as research candidates.

The evaluation pipeline may:

- normalize discovered data
- enrich with available market data
- run the controlled analysis workflow
- create a risk summary
- create a review item

The evaluation pipeline must not:

- approve a source automatically
- ingest into RAG without review
- create trade instructions
- hide missing data

## 9. Paid API Policy

Paid APIs should not be required for the MVP or for the first post-MVP source monitoring implementation.

Premium providers may be added as optional future adapters after the public/free architecture is stable.
