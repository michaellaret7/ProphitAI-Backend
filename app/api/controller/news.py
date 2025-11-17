import asyncio
from fastapi import HTTPException
from typing import Dict, Any, Optional
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_stock_news_controller(
    ticker: str,
    limit: int = 1000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle stock news data retrieval for a ticker from FMP
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_stock_news, ticker=ticker, limit=limit, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve stock news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Stock news retrieved successfully",
        kind="news#stockNews",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/stock-news",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


@handle_controller_errors
async def get_press_releases_controller(
    ticker: str,
    limit: int = 1000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle press releases data retrieval for a ticker from FMP
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_press_releases, ticker=ticker, limit=limit, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve press releases from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Press releases retrieved successfully",
        kind="news#pressReleases",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/press-releases",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


@handle_controller_errors
async def get_price_target_news_controller(
    ticker: str,
    page: int = 0,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Controller to handle price target news data retrieval for a ticker from FMP
    Note: FMP price target news endpoint uses pagination (page) instead of date filtering
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_price_target_news, ticker=ticker, page=page, limit=limit)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve price target news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Price target news retrieved successfully",
        kind="news#priceTargets",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/price-targets",
        counts={"totalItems": len(items), "currentItemCount": len(items), "startIndex": page * limit},
        payload=items,
    )


@handle_controller_errors
async def get_stock_grade_news_controller(
    ticker: str,
    page: int = 0,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Controller to handle stock grade/rating news data retrieval for a ticker from FMP
    Note: FMP stock grade news endpoint uses pagination (page) instead of date filtering
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_stock_grade_news, ticker=ticker, page=page, limit=limit)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve stock grade news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Stock grade news retrieved successfully",
        kind="news#stockGrades",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/stock-grades",
        counts={"totalItems": len(items), "currentItemCount": len(items), "startIndex": page * limit},
        payload=items,
    )


@handle_controller_errors
async def get_general_news_controller(
    limit: int = 1000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle general news retrieval from FMP
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_general_news, limit=limit, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve general news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="General news retrieved successfully",
        kind="news#general",
        self_link="/api/news/general",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


@handle_controller_errors
async def get_fmp_articles_controller(
    page: int = 0,
    limit: int = 1000,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle FMP articles retrieval
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_fmp_articles, page=page, limit=limit, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve FMP articles from API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="FMP articles retrieved successfully",
        kind="news#fmpArticles",
        self_link=f"/api/news/fmp-articles?page={page}&limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items), "startIndex": page * limit},
        payload=items,
    )
