from fastapi import APIRouter, Query, Path
from typing import Optional
from prophitai_api.controllers.news import (
    get_stock_news_controller,
    get_batch_stock_news_controller,
    get_press_releases_controller,
    get_price_target_news_controller,
    get_stock_grade_news_controller,
    get_general_news_controller,
    get_fmp_articles_controller,
)
from prophitai_api.schemas.news import BatchStockNewsRequest

router = APIRouter(tags=["News & Media 📰"])


@router.get("/news/{ticker}/stock-news")
async def get_stock_news(
    ticker: str = Path(..., description="Stock ticker symbol"),
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of news items to return"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)"),
):
    """
    Get general stock news for a ticker from FMP

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        limit: Maximum number of news items to return (default: 1000, max: 1000)
        from_date: Optional start date for filtering news (YYYY-MM-DD format)
        to_date: Optional end date for filtering news (YYYY-MM-DD format)

    Returns:
        News items with published date, title, publisher, site, text content, image URL, and article URL
    """
    return await get_stock_news_controller(
        ticker=ticker,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
    )


@router.post("/news/stock-news/batch")
async def get_batch_stock_news(body: BatchStockNewsRequest):
    """
    Get stock news for multiple tickers in a single request.

    Efficient batch endpoint that fetches news for up to 5 tickers at once
    using FMP's stock news API with comma-separated symbols.

    Returns news items grouped by ticker for easy consumption.

    Response payload structure:
    - news_by_ticker: Dictionary mapping ticker -> list of news items
    - tickers_without_news: List of tickers that had no news

    News items include:
    - publishedDate, title, publisher, site
    - text (content), image URL, article URL
    - symbol (ticker the news is about)

    Args:
        tickers: List of stock ticker symbols (max 5)
        limit: Max news items to return (default: 100, max: 500)
        from_date: Optional start date filter (YYYY-MM-DD)
        to_date: Optional end date filter (YYYY-MM-DD)

    Example request body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "limit": 50,
        "from_date": "2026-01-01",
        "to_date": "2026-01-15"
    }
    """
    return await get_batch_stock_news_controller(
        tickers=body.tickers,
        limit=body.limit,
        from_date=body.from_date,
        to_date=body.to_date,
    )


@router.get("/news/{ticker}/press-releases")
async def get_press_releases(
    ticker: str = Path(..., description="Stock ticker symbol"),
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of press releases to return"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)"),
):
    """
    Get company press releases for a ticker from FMP

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        limit: Maximum number of press releases to return (default: 1000, max: 1000)
        from_date: Optional start date for filtering press releases (YYYY-MM-DD format)
        to_date: Optional end date for filtering press releases (YYYY-MM-DD format)

    Returns:
        Press releases with published date, title, publisher, site, text content, image URL, and article URL
    """
    return await get_press_releases_controller(
        ticker=ticker,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/news/{ticker}/price-targets")
async def get_price_target_news(
    ticker: str = Path(..., description="Stock ticker symbol"),
    page: int = Query(0, ge=0, description="Page number for pagination (starts at 0)"),
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of price target news items to return per page"),
):
    """
    Get analyst price target news for a ticker from FMP

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        page: Page number for pagination (default: 0)
        limit: Maximum number of price target news items to return per page (default: 1000, max: 1000)

    Returns:
        Price target news with analyst name, company, price target, adjusted price target,
        price when posted, news publisher information, and article URL

    Note:
        This endpoint uses pagination instead of date filtering
    """
    return await get_price_target_news_controller(
        ticker=ticker,
        page=page,
        limit=limit,
    )


@router.get("/news/{ticker}/stock-grades")
async def get_stock_grade_news(
    ticker: str = Path(..., description="Stock ticker symbol"),
    page: int = Query(0, ge=0, description="Page number for pagination (starts at 0)"),
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of stock grade news items to return per page"),
):
    """
    Get analyst stock grade/rating news for a ticker from FMP

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        page: Page number for pagination (default: 0)
        limit: Maximum number of stock grade news items to return per page (default: 1000, max: 1000)

    Returns:
        Stock grade news with grading company, new grade, previous grade, action,
        price when posted, news publisher information, and article URL

    Note:
        This endpoint uses pagination instead of date filtering
    """
    return await get_stock_grade_news_controller(
        ticker=ticker,
        page=page,
        limit=limit,
    )


@router.get("/news/general")
async def get_general_news(
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of news items to return"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)")
):
    """
    Get general market news (not ticker-specific)

    Args:
        limit: Maximum number of news items to return (default: 1000, max: 1000)
        from_date: Optional start date for filtering news (YYYY-MM-DD format)
        to_date: Optional end date for filtering news (YYYY-MM-DD format)

    Returns:
        General news items with published date, title, publisher, site, text content, image URL, and article URL
    """
    return await get_general_news_controller(limit=limit, from_date=from_date, to_date=to_date)


@router.get("/news/fmp-articles")
async def get_fmp_articles(
    page: int = Query(0, ge=0, description="Page number for pagination (starts at 0)"),
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of articles to return per page"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)")
):
    """
    Get FMP articles (Financial Modeling Prep original content)

    Args:
        page: Page number for pagination (default: 0)
        limit: Maximum number of articles to return per page (default: 1000, max: 1000)
        from_date: Optional start date for filtering articles (YYYY-MM-DD format)
        to_date: Optional end date for filtering articles (YYYY-MM-DD format)

    Returns:
        FMP articles with date, title, content, image URL, link, author, and tags
    """
    return await get_fmp_articles_controller(page=page, limit=limit, from_date=from_date, to_date=to_date)
