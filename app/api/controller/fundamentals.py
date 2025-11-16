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
from app.db.core.pull_fmp_data import FMP_API_DATA


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


@handle_controller_errors
async def get_stock_peers_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle stock peers data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_stock_peers(ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No peer data found for {ticker}",
            kind="fundamentals#stockPeers",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/peers",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Stock peers retrieved successfully",
        kind="fundamentals#stockPeers",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/peers",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_esg_disclosures_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle ESG disclosures data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_esg_disclosures(ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No ESG data found for {ticker}",
            kind="fundamentals#esgDisclosures",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/esg",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="ESG disclosures retrieved successfully",
        kind="fundamentals#esgDisclosures",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/esg",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_revenue_product_segmentation_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle revenue product segmentation data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_revenue_product_segmentation(ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No revenue product segmentation data found for {ticker}",
            kind="fundamentals#revenueProductSegmentation",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/revenue/product-segmentation",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Revenue product segmentation retrieved successfully",
        kind="fundamentals#revenueProductSegmentation",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/revenue/product-segmentation",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_revenue_geographic_segmentation_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle revenue geographic segmentation data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_revenue_geographic_segmentation(ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No revenue geographic segmentation data found for {ticker}",
            kind="fundamentals#revenueGeographicSegmentation",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/revenue/geographic-segmentation",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Revenue geographic segmentation retrieved successfully",
        kind="fundamentals#revenueGeographicSegmentation",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/revenue/geographic-segmentation",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_institutional_holder_analytics_controller(
    ticker: str,
    year: int,
    quarter: int,
) -> Dict[str, Any]:
    """
    Controller to handle institutional holder analytics data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_institutional_holder_analytics(ticker, year, quarter)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No institutional holder analytics data found for {ticker} ({year} Q{quarter})",
            kind="fundamentals#institutionalHolderAnalytics",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/ownership/institutional-analytics?year={year}&quarter={quarter}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Institutional holder analytics retrieved successfully",
        kind="fundamentals#institutionalHolderAnalytics",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/ownership/institutional-analytics?year={year}&quarter={quarter}",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_institutional_positions_summary_controller(
    ticker: str,
    year: int,
    quarter: int,
) -> Dict[str, Any]:
    """
    Controller to handle institutional positions summary data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_institutional_positions_summary(ticker, year, quarter)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No institutional positions summary data found for {ticker} ({year} Q{quarter})",
            kind="fundamentals#institutionalPositionsSummary",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/ownership/institutional-positions?year={year}&quarter={quarter}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload={},
        )

    return ok_envelope(
        message="Institutional positions summary retrieved successfully",
        kind="fundamentals#institutionalPositionsSummary",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/ownership/institutional-positions?year={year}&quarter={quarter}",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )


@handle_controller_errors
async def get_company_notes_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to handle company notes and bonds data retrieval for a ticker
    """
    fmp_api = FMP_API_DATA()
    data = fmp_api.get_company_notes(ticker)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No company notes data found for {ticker}",
            kind="fundamentals#companyNotes",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/company-notes",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Company notes retrieved successfully",
        kind="fundamentals#companyNotes",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/company-notes",
        counts={"totalItems": len(data) if isinstance(data, list) else 1, "currentItemCount": len(data) if isinstance(data, list) else 1},
        payload=data,
    )
