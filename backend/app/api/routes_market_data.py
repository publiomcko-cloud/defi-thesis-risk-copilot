from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.market_data import MarketDataRequest, MarketDataResponse
from app.services.market_data_service import fetch_market_data_summary

router = APIRouter(tags=["market data"])


@router.post("/market-data/fetch", response_model=MarketDataResponse)
def fetch_market_data(
    request: MarketDataRequest,
    db: Session = Depends(get_db),
) -> MarketDataResponse:
    return fetch_market_data_summary(request, db)
