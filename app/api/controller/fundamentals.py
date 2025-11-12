from fastapi import HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
from app.repositories.fundamental_data import get_fundamental_data
from app.repositories.ratings_data import (
    get_analyst_recommendations,
    get_price_target_summary,
    get_stock_grades_individual,
    get_stock_grades_summary,
    get_ratings,
)
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_analyst_estimates_controller(
    ticker: str,
    quarters_back: int = 4,
    simulation_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Controller to handle analyst estimates data retrieval for a ticker
    """
    # Delegate to repository
    data = get_fundamental_data(
        ticker=ticker,
        statement_type="analyst_estimates",
        quarters_back=quarters_back,
        _simulation_date=simulation_date,
    )

    return ok_envelope(
        message="Analyst estimates retrieved successfully",
        kind="fundamentals#analystEstimates",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/analyst-estimates",
        counts={"totalItems": len(data['data']), "currentItemCount": len(data['data'])},
        payload=data['data'],
    )


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
async def get_stock_grades_individual_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Controller to handle individual stock grades data retrieval for a ticker
    """
    # Delegate to repository
    data = get_stock_grades_individual(
        ticker=ticker,
        start=start_date,
        end=end_date,
    )

    return ok_envelope(
        message="Individual stock grades retrieved successfully",
        kind="fundamentals#stockGradesIndividual",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/grades/individual",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
    )


@handle_controller_errors
async def get_stock_grades_summary_controller(
    ticker: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Controller to handle aggregated stock grades summary data retrieval for a ticker
    """
    # Delegate to repository
    data = get_stock_grades_summary(
        ticker=ticker,
        start=start_date,
        end=end_date,
    )

    return ok_envelope(
        message="Stock grades summary retrieved successfully",
        kind="fundamentals#stockGradesSummary",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/grades/summary",
        counts={"totalItems": data['count'], "currentItemCount": data['count']},
        payload=data['items'],
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
