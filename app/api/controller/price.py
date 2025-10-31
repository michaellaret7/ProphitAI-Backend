from fastapi import HTTPException
from typing import Dict, Any, List
from app.services.shared import PriceService
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_stock_prices_controller(tickers: List[str], days: int) -> Dict[str, Any]:
    """
    Controller to handle stock price data retrieval for multiple tickers
    """
    # Delegate to service
    service = PriceService()
    data = service.get_stock_prices(tickers=tickers, days=days)

    return ok_envelope(
        message="Stock price data retrieved successfully",
        kind="price#stockPrices",
        resource_id=",".join(tickers),
        self_link=f"/api/price/stocks",
        counts=data['counts'],
        payload=data['payload'],
    )
