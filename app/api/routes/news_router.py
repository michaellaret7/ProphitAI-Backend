from fastapi import APIRouter, Query, Path, Depends
from typing import Optional
from datetime import datetime
from app.api.controller.news import (
    get_stock_news_controller,
    get_press_releases_controller,
    get_price_target_news_controller,
    get_stock_grade_news_controller,
)
from app.models.news_models import NewsRequest

router = APIRouter()


def parse_news_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    limit: Optional[int] = Query(None, gt=0, le=1000, description="Maximum number of items to return"),
    ascending: bool = Query(True, description="Sort by date ascending (true) or descending (false)"),
) -> NewsRequest:
    """Parse and validate query parameters into NewsRequest model"""
    # Convert string dates to datetime objects if provided
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    return NewsRequest(
        ticker=ticker,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
        ascending=ascending,
    )


@router.get("/news/{ticker}/stock-news")
async def get_stock_news(
    request: NewsRequest = Depends(parse_news_request)
):
    """
    Get general stock news for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering news
        end_date: Optional end date for filtering news
        limit: Optional maximum number of news items to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        News items with published date, title, publisher, site, and text content
    """
    return await get_stock_news_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
        ascending=request.ascending,
    )


@router.get("/news/{ticker}/press-releases")
async def get_press_releases(
    request: NewsRequest = Depends(parse_news_request)
):
    """
    Get company press releases for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering press releases
        end_date: Optional end date for filtering press releases
        limit: Optional maximum number of press releases to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Press releases with published date, title, publisher, site, and text content
    """
    return await get_press_releases_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
        ascending=request.ascending,
    )


@router.get("/news/{ticker}/price-targets")
async def get_price_target_news(
    request: NewsRequest = Depends(parse_news_request)
):
    """
    Get analyst price target news for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering price target news
        end_date: Optional end date for filtering price target news
        limit: Optional maximum number of price target news items to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Price target news with analyst name, company, price target, adjusted price target,
        price when posted, and news publisher information
    """
    return await get_price_target_news_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
        ascending=request.ascending,
    )


@router.get("/news/{ticker}/stock-grades")
async def get_stock_grade_news(
    request: NewsRequest = Depends(parse_news_request)
):
    """
    Get analyst stock grade/rating news for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering stock grade news
        end_date: Optional end date for filtering stock grade news
        limit: Optional maximum number of stock grade news items to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Stock grade news with grading company, new grade, previous grade, action,
        price when posted, and news publisher information
    """
    return await get_stock_grade_news_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
        ascending=request.ascending,
    )
