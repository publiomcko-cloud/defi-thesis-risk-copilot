# Internal DeFi Risk Notes

## Liquidation Risk

Liquidation risk is the risk that a collateralized borrowing position can be liquidated because collateral value falls, debt value rises, interest accrues, or protocol parameters change. Monitoring should include LTV, liquidation thresholds, borrow rates, and collateral volatility.

## Composability Risk

Composability risk increases when a strategy combines multiple protocols. A Pendle PT strategy funded through Morpho borrow combines maturity risk, liquidity risk, oracle risk, borrow rate risk, and liquidation risk.

## Missing Data

Missing data should be visible in reports. Unknown liquidity, stale market prices, missing oracle details, or absent borrow APY should reduce confidence rather than be silently inferred.
