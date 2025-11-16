from fastapi import HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
from app.repositories.news_data import (
    get_stock_news,
    get_press_releases,
    get_price_target_news,
    get_stock_grade_news,
)
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_stock_news_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """
    Controller to handle stock news data retrieval for a ticker
    """
    # Delegate to repository
    data = get_stock_news(
        ticker=ticker,
        start=start_date,
        end=end_date,
        limit=limit,
        ascending=ascending,
    )

    return ok_envelope(
        message="Stock news retrieved successfully",
        kind="news#stockNews",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/stock-news",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_press_releases_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """
    Controller to handle press releases data retrieval for a ticker
    """
    # Delegate to repository
    data = get_press_releases(
        ticker=ticker,
        start=start_date,
        end=end_date,
        limit=limit,
        ascending=ascending,
    )

    return ok_envelope(
        message="Press releases retrieved successfully",
        kind="news#pressReleases",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/press-releases",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_price_target_news_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """
    Controller to handle price target news data retrieval for a ticker
    """
    # Delegate to repository
    data = get_price_target_news(
        ticker=ticker,
        start=start_date,
        end=end_date,
        limit=limit,
        ascending=ascending,
    )

    return ok_envelope(
        message="Price target news retrieved successfully",
        kind="news#priceTargets",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/price-targets",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_stock_grade_news_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """
    Controller to handle stock grade/rating news data retrieval for a ticker
    """
    # Delegate to repository
    data = get_stock_grade_news(
        ticker=ticker,
        start=start_date,
        end=end_date,
        limit=limit,
        ascending=ascending,
    )

    return ok_envelope(
        message="Stock grade news retrieved successfully",
        kind="news#stockGrades",
        resource_id=ticker,
        self_link=f"/api/news/{ticker}/stock-grades",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_general_news_controller(
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Controller to handle general news retrieval from FMP
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_general_news(limit=limit)

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
) -> Dict[str, Any]:
    """
    Controller to handle FMP articles retrieval
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_fmp_articles(page=page, limit=limit)

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
