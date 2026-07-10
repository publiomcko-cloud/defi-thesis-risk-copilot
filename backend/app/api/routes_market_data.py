from fastapi import APIRouter

from app.schemas.market_data import MarketDataRequest, MarketDataResponse

router = APIRouter(tags=["market data"])


@router.post("/market-data/fetch", response_model=MarketDataResponse)
def fetch_market_data(request: MarketDataRequest) -> MarketDataResponse:
    protocols = [protocol.lower() for protocol in request.protocols]
    return MarketDataResponse(
        status="mocked",
        source="manual_or_placeholder",
        data={
            "protocols": protocols,
            "market_url": request.market_url,
            "manual_inputs": request.manual_inputs,
        },
        missing_fields=[
            "live_token_prices",
            "live_liquidity",
            "live_borrow_rates",
            "oracle_metadata",
        ],
        assumptions=[
            "Phase 2 does not call external market APIs.",
            "Manual inputs are passed through as user-provided placeholders.",
        ],
    )
