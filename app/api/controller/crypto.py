import asyncio
from fastapi import HTTPException
from typing import Dict, Any, Optional
from app.services.crypto.news import CryptoNewsService
from app.services.crypto.price import CryptoPriceService
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_crypto_news_general_controller(
    limit: int = 1000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle general crypto news retrieval from FMP
    """
    crypto_news_service = CryptoNewsService()

    # Reason: Service method already handles async operations internally
    data = await crypto_news_service.get_crypto_news_general(
        row_limit=limit,
        from_date=from_date,
        to_date=to_date
    )

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve crypto news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Crypto news retrieved successfully",
        kind="crypto#news",
        self_link=f"/api/crypto/news?limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


@handle_controller_errors
async def get_crypto_news_by_symbol_controller(
    symbol: str,
    limit: int = 250,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle crypto news retrieval for a specific symbol from FMP
    """
    crypto_news_service = CryptoNewsService()

    # Reason: Service method already handles async operations internally
    data = await crypto_news_service.get_crypto_news_by_symbol(
        symbol=symbol,
        row_limit=limit,
        from_date=from_date,
        to_date=to_date
    )

    if data is None:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve crypto news for {symbol} from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message=f"Crypto news for {symbol} retrieved successfully",
        kind="crypto#symbolNews",
        resource_id=symbol,
        self_link=f"/api/crypto/{symbol}/news?limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


@handle_controller_errors
async def get_crypto_price_controller(
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    technical_indicators: bool = True,
) -> Dict[str, Any]:
    """
    Controller to handle crypto EOD price data retrieval for a specific symbol from FMP
    """
    crypto_price_service = CryptoPriceService()

    # Reason: Service method already handles async operations internally
    data = await crypto_price_service.get_crypto_eod_price_by_symbol(
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        technical_indicators=technical_indicators
    )

    if data is None or (hasattr(data, 'empty') and data.empty):
        raise HTTPException(status_code=500, detail=f"Failed to retrieve price data for {symbol} from FMP API")

    # Convert DataFrame to list of records
    items = data.to_dict(orient='records') if hasattr(data, 'to_dict') else []

    return ok_envelope(
        message=f"Price data for {symbol} retrieved successfully",
        kind="crypto#price",
        resource_id=symbol,
        self_link=f"/api/crypto/{symbol}/price",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )

