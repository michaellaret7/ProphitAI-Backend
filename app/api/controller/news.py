from fastapi import HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
from app.repositories.news_data import (
    get_stock_news,
    get_press_releases,
    get_price_target_news,
    get_stock_grade_news,
)
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
