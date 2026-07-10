from sqlalchemy.orm import Session

from app.agents.strategy_parser import ParsedStrategy
from app.schemas.market_data import MarketDataRequest, MarketDataResponse
from app.services.market_data_service import fetch_market_data_summary


def fetch_strategy_market_data(
    parsed_strategy: ParsedStrategy,
    db: Session,
) -> MarketDataResponse:
    return fetch_market_data_summary(
        MarketDataRequest(
            protocols=parsed_strategy.protocols,
            market_url=parsed_strategy.market_url,
            manual_inputs=parsed_strategy.manual_inputs,
        ),
        db,
    )
