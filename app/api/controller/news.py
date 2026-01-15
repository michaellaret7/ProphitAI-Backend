import asyncio
from fastapi import HTTPException
from typing import Dict, Any, List, Optional
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
async def get_batch_stock_news_controller(
    tickers: List[str],
    limit: int = 100,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to retrieve stock news for multiple tickers in a single request.

    Uses FMP's stock news API with comma-separated symbols.
    No caching since news is time-sensitive.

    Args:
        tickers: List of stock ticker symbols (max 5)
        limit: Maximum news items to return (default: 100, max: 500)
        from_date: Optional start date filter (YYYY-MM-DD)
        to_date: Optional end date filter (YYYY-MM-DD)

    Returns:
        Response envelope with batch stock news payload
    """
    fmp_api = FMP_API_DATA()

    # Reason: Use batch method to fetch news for all tickers in single API call
    data = await asyncio.to_thread(
        fmp_api.get_batch_stock_news,
        tickers=tickers,
        limit=limit,
        from_date=from_date,
        to_date=to_date
    )

    if data is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve stock news from FMP API"
        )

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    # Group news by ticker for organized response
    news_by_ticker: Dict[str, List] = {ticker: [] for ticker in tickers}

    for item in items:
        # Reason: FMP news includes 'symbol' field to identify which ticker it's for
        ticker = item.get('symbol', '').upper()
        if ticker in news_by_ticker:
            news_by_ticker[ticker].append(item)

    # Identify tickers with no news found
    tickers_with_news = [t for t in tickers if news_by_ticker[t]]
    tickers_without_news = [t for t in tickers if not news_by_ticker[t]]

    return ok_envelope(
        message=f"Batch stock news retrieved ({len(tickers_with_news)} tickers with news, {len(tickers_without_news)} without)",
        kind="news#batchStockNews",
        resource_id=",".join(sorted(tickers)),
        self_link="/api/news/stock-news/batch",
        counts={
            "totalRequested": len(tickers),
            "tickersWithNews": len(tickers_with_news),
            "tickersWithoutNews": len(tickers_without_news),
            "totalNewsItems": len(items)
        },
        payload={
            "news_by_ticker": news_by_ticker,
            "tickers_without_news": tickers_without_news
        },
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

@handle_controller_errors
async def get_crpyto_news_general_controller(
    limit: int = 1000,
    page: int = 1
) -> Dict[str, Any]:
    """
    Controller to handle crypto news general retrieval from FMP
    """
    fmp_api = FMP_API_DATA()
    data = await asyncio.to_thread(fmp_api.get_latest_crypto_news, page=page, limit=limit)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve crypto news from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Crypto news retrieved successfully",
        kind="news#cryptoNews",
        self_link=f"/api/news/crypto-news?limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items
    )

if __name__ == "__main__":
    import asyncio
    import pandas as pd
    from app.db.core.pull_fmp_data import FMP_API_DATA
    fmp_api = FMP_API_DATA()
    data = asyncio.run(get_crpyto_news_general_controller())
    # print(data['data']['payload'])
    df = pd.DataFrame(data['data']['payload'])
    pd.set_option('display.max_rows', None)
    print(df)
