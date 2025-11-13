from fastapi import APIRouter, Query, Path, Depends
from typing import Optional
from datetime import datetime
from app.api.controller.fundamentals import (
    get_analyst_estimates_controller,
    get_analyst_recommendations_controller,
    get_price_target_summary_controller,
    get_stock_grades_individual_controller,
    get_stock_grades_summary_controller,
    get_ratings_controller,
    get_stock_peers_controller,
    get_esg_disclosures_controller,
    get_revenue_product_segmentation_controller,
    get_revenue_geographic_segmentation_controller,
    get_institutional_holder_analytics_controller,
    get_institutional_positions_summary_controller,
)
from app.models.fundamentals_models import (
    AnalystEstimatesRequest,
    AnalystDataRequest,
    PriceTargetRequest,
)
from app.models.company_models import (
    PeersRequest,
    ESGRequest,
    RevenueSegmentationRequest,
    InstitutionalOwnershipRequest,
)

router = APIRouter()


def parse_analyst_estimates_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
    quarters_back: int = Query(4, gt=0, le=20, description="Number of quarters of estimates to retrieve"),
    simulation_date: Optional[str] = Query(None, description="Simulation date for backtesting (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
) -> AnalystEstimatesRequest:
    """Parse and validate query parameters into AnalystEstimatesRequest model"""
    # Convert string date to datetime object if provided
    sim_dt = datetime.fromisoformat(simulation_date) if simulation_date else None

    return AnalystEstimatesRequest(
        ticker=ticker,
        quarters_back=quarters_back,
        simulation_date=sim_dt,
    )


def parse_analyst_data_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    limit: Optional[int] = Query(None, gt=0, le=1000, description="Maximum number of items to return"),
    ascending: bool = Query(True, description="Sort by date ascending (true) or descending (false)"),
) -> AnalystDataRequest:
    """Parse and validate query parameters into AnalystDataRequest model"""
    # Convert string dates to datetime objects if provided
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    return AnalystDataRequest(
        ticker=ticker,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
        ascending=ascending,
    )


def parse_price_target_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
) -> PriceTargetRequest:
    """Parse and validate ticker into PriceTargetRequest model"""
    return PriceTargetRequest(ticker=ticker)


@router.get("/fundamentals/{ticker}/analyst-estimates")
async def get_analyst_estimates(
    request: AnalystEstimatesRequest = Depends(parse_analyst_estimates_request)
):
    """
    Get analyst estimates for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        quarters_back: Number of quarters of estimates to retrieve (default: 4, max: 20)
        simulation_date: Optional simulation date for backtesting purposes

    Returns:
        Analyst estimates including EPS average/high/low, Revenue average/high/low,
        EBITDA average, EBIT average, and Net Income average for each quarter
    """
    return await get_analyst_estimates_controller(
        ticker=request.ticker,
        quarters_back=request.quarters_back,
        simulation_date=request.simulation_date,
    )


@router.get("/fundamentals/{ticker}/analyst-recommendations")
async def get_analyst_recommendations(
    request: AnalystDataRequest = Depends(parse_analyst_data_request)
):
    """
    Get analyst recommendations for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering recommendations
        end_date: Optional end date for filtering recommendations
        limit: Optional maximum number of recommendations to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Analyst recommendations with rating, rating score, and rating recommendation
    """
    return await get_analyst_recommendations_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
    )


@router.get("/fundamentals/{ticker}/price-targets")
async def get_price_target_summary(
    request: PriceTargetRequest = Depends(parse_price_target_request)
):
    """
    Get price target summary for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Price target summary including average price targets and analyst counts for
        last month, last quarter, last year, and all-time periods
    """
    return await get_price_target_summary_controller(
        ticker=request.ticker,
    )


@router.get("/fundamentals/{ticker}/grades/individual")
async def get_stock_grades_individual(
    request: AnalystDataRequest = Depends(parse_analyst_data_request)
):
    """
    Get individual analyst grade changes for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering grades
        end_date: Optional end date for filtering grades
        limit: Optional maximum number of grades to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Individual analyst grade changes with grading company, previous grade,
        new grade, and action (upgrade/downgrade/initiated/reiterated)
    """
    return await get_stock_grades_individual_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
    )


@router.get("/fundamentals/{ticker}/grades/summary")
async def get_stock_grades_summary(
    request: AnalystDataRequest = Depends(parse_analyst_data_request)
):
    """
    Get aggregated stock grades summary for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering grades
        end_date: Optional end date for filtering grades
        limit: Optional maximum number of summaries to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Aggregated counts of strong buy, buy, hold, sell, and strong sell ratings
    """
    return await get_stock_grades_summary_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
    )


@router.get("/fundamentals/{ticker}/ratings")
async def get_ratings(
    request: AnalystDataRequest = Depends(parse_analyst_data_request)
):
    """
    Get stock ratings with detailed scoring for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        start_date: Optional start date for filtering ratings
        end_date: Optional end date for filtering ratings
        limit: Optional maximum number of ratings to return (default: all)
        ascending: Sort order by date (default: true for oldest first)

    Returns:
        Stock ratings with overall rating and individual scores for DCF (discounted cash flow),
        ROE (return on equity), ROA (return on assets), D/E (debt to equity),
        P/E (price to earnings), and P/B (price to book) ratios
    """
    return await get_ratings_controller(
        ticker=request.ticker,
        start_date=request.start_date,
        end_date=request.end_date,
    )


def parse_peers_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
) -> PeersRequest:
    """Parse and validate ticker into PeersRequest model"""
    return PeersRequest(ticker=ticker)


def parse_esg_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
) -> ESGRequest:
    """Parse and validate ticker into ESGRequest model"""
    return ESGRequest(ticker=ticker)


def parse_revenue_segmentation_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
) -> RevenueSegmentationRequest:
    """Parse and validate ticker into RevenueSegmentationRequest model"""
    return RevenueSegmentationRequest(ticker=ticker)


def parse_institutional_ownership_request(
    ticker: str = Path(..., description="Stock ticker symbol"),
    year: int = Query(..., description="Year (e.g., 2025)", ge=2000, le=2100),
    quarter: int = Query(..., description="Quarter (1-4)", ge=1, le=4),
) -> InstitutionalOwnershipRequest:
    """Parse and validate parameters into InstitutionalOwnershipRequest model"""
    return InstitutionalOwnershipRequest(ticker=ticker, year=year, quarter=quarter)


@router.get("/fundamentals/{ticker}/peers")
async def get_stock_peers(
    request: PeersRequest = Depends(parse_peers_request)
):
    """
    Get peer companies for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        List of peer companies in the same sector/industry
    """
    return await get_stock_peers_controller(ticker=request.ticker)


@router.get("/fundamentals/{ticker}/esg")
async def get_esg_disclosures(
    request: ESGRequest = Depends(parse_esg_request)
):
    """
    Get ESG (Environmental, Social, Governance) disclosures for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        ESG ratings and sustainability metrics
    """
    return await get_esg_disclosures_controller(ticker=request.ticker)


@router.get("/fundamentals/{ticker}/revenue/product-segmentation")
async def get_revenue_product_segmentation(
    request: RevenueSegmentationRequest = Depends(parse_revenue_segmentation_request)
):
    """
    Get revenue breakdown by product segments for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Revenue segmentation data broken down by product lines/segments
    """
    return await get_revenue_product_segmentation_controller(ticker=request.ticker)


@router.get("/fundamentals/{ticker}/revenue/geographic-segmentation")
async def get_revenue_geographic_segmentation(
    request: RevenueSegmentationRequest = Depends(parse_revenue_segmentation_request)
):
    """
    Get revenue breakdown by geographic regions for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Revenue segmentation data broken down by geographic regions
    """
    return await get_revenue_geographic_segmentation_controller(ticker=request.ticker)


@router.get("/fundamentals/{ticker}/ownership/institutional-analytics")
async def get_institutional_holder_analytics(
    request: InstitutionalOwnershipRequest = Depends(parse_institutional_ownership_request)
):
    """
    Get institutional ownership analytics for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        year: Year (e.g., 2025)
        quarter: Quarter (1-4)

    Returns:
        Institutional holder analytics data for the specified quarter
    """
    return await get_institutional_holder_analytics_controller(
        ticker=request.ticker,
        year=request.year,
        quarter=request.quarter,
    )


@router.get("/fundamentals/{ticker}/ownership/institutional-positions")
async def get_institutional_positions_summary(
    request: InstitutionalOwnershipRequest = Depends(parse_institutional_ownership_request)
):
    """
    Get institutional ownership positions summary for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        year: Year (e.g., 2025)
        quarter: Quarter (1-4)

    Returns:
        Summary of institutional positions for the specified quarter
    """
    return await get_institutional_positions_summary_controller(
        ticker=request.ticker,
        year=request.year,
        quarter=request.quarter,
    )
