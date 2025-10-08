from fastapi import HTTPException
from typing import Dict, Any, List
from app.services.price import PriceService
from app.api.response_envelope import ok_envelope


async def get_stock_prices_controller(tickers: List[str], days: int) -> Dict[str, Any]:
    """
    Controller to handle stock price data retrieval for multiple tickers
    """
    try:
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
