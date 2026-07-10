# Morpho Notes

## LLTV

Morpho markets use a loan-to-value constraint often described as LLTV, or liquidation loan-to-value. LLTV defines the maximum borrowable value relative to collateral before a position becomes unsafe or liquidatable.

## Borrow Rate Risk

Morpho borrow rates may change with market utilization and liquidity conditions. A strategy that borrows against collateral can lose its positive spread if the variable borrow APY rises.

## Oracle Context

Morpho markets depend on configured oracle sources for collateral and loan asset valuation. Oracle risk is important because stale, manipulated, delayed, or unsuitable price data can affect liquidation safety.
