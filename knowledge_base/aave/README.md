# Aave Notes

## Health Factor

Aave uses Health Factor to express how close a position is to liquidation. A higher Health Factor means more buffer, while a Health Factor below the liquidation threshold indicates that a position can be liquidated.

## Liquidation Risk

Liquidation risk can come from collateral price declines, debt growth, rising borrow rates, collateral parameter changes, or oracle issues. Leveraged strategies need a monitoring plan for Health Factor and collateral volatility.

## Lending Market Parameters

Aave reserve parameters include supply rates, borrow rates, collateral eligibility, liquidation thresholds, and loan-to-value limits. These values should be treated as market data inputs and checked for freshness.
