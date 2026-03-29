"""Controllers for ratings and price target endpoints."""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_data.repositories.ratings import (
    get_analyst_recommendations,
    get_price_target_summary,
    get_ratings,
)
from prophitai_data.clients.fmp import FMP_API_DATA


@handle_controller_errors
async def get_analyst_recommendations_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Controller to handle analyst recommendations data retrieval for a ticker
    """
    # Delegate to repository
    data = get_analyst_recommendations(
        ticker=ticker,
        start=start_date,
        end=end_date,
    )

    return ok_envelope(
        message="Analyst recommendations retrieved successfully",
        kind="fundamentals#analystRecommendations",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/analyst-recommendations",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_price_target_summary_controller(
    ticker: str,
) -> Dict[str, Any]:
    """
    Controller to handle price target summary data retrieval for a ticker
    """
    # Delegate to repository
    data = get_price_target_summary(ticker=ticker)

    # Handle case where ticker has no price target data
    if not data.get('found', False):
        return ok_envelope(
            message=f"No price target data found for {ticker}",
            kind="fundamentals#priceTargetSummary",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/price-targets",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Price target summary retrieved successfully",
        kind="fundamentals#priceTargetSummary",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/price-targets",
        counts={"totalItems": 1, "currentItemCount": 1},
        payload=data,
    )


@handle_controller_errors
async def get_price_target_consensus_controller(
    ticker: str,
) -> Dict[str, Any]:
    """
    Controller to handle price target consensus data retrieval for a ticker
    """
    fmp = FMP_API_DATA()
    data = await asyncio.to_thread(fmp.get_price_target_consensus, ticker)

    if not data:
        return ok_envelope(
            message=f"No price target consensus data found for {ticker}",
            kind="fundamentals#priceTargetConsensus",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/price-target-consensus",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Price target consensus retrieved successfully",
        kind="fundamentals#priceTargetConsensus",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/price-target-consensus",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_stock_grades_individual_controller(
    ticker: str,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Controller to handle individual stock grades data retrieval for a ticker

    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of grades to return (default: 500)
    """
    fmp = FMP_API_DATA()
    data = await asyncio.to_thread(fmp.get_stock_grades_individual, ticker, limit=limit)

    if not data:
        return ok_envelope(
            message=f"No stock grades individual data found for {ticker}",
            kind="fundamentals#stockGradesIndividual",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/grades/individual",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    # Reason: FMP API doesn't respect limit parameter, so we slice the data manually
    limited_data = data[:limit]

    return ok_envelope(
        message="Individual stock grades retrieved successfully",
        kind="fundamentals#stockGradesIndividual",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/grades/individual",
        counts={"totalItems": len(limited_data), "currentItemCount": len(limited_data)},
        payload=limited_data,
    )


@handle_controller_errors
async def get_stock_grades_summary_controller(
    ticker: str,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Controller to handle aggregated stock grades summary data retrieval for a ticker
    """

    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(fmp_api.get_stock_grades_summary, ticker, limit=limit)

    if not data:
        return ok_envelope(
            message=f"No stock grades summary data found for {ticker}",
            kind="fundamentals#stockGradesSummary",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/grades/summary",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Stock grades summary retrieved successfully",
        kind="fundamentals#stockGradesSummary",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/grades/summary",
        counts={"totalItems": len(data), "currentItemCount": len(data)},
        payload=data,
    )


@handle_controller_errors
async def get_ratings_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Controller to handle stock ratings data retrieval for a ticker
    """
    # Delegate to repository
    data = get_ratings(
        ticker=ticker,
        start=start_date,
        end=end_date,
    )

    return ok_envelope(
        message="Stock ratings retrieved successfully",
        kind="fundamentals#ratings",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/ratings",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )
