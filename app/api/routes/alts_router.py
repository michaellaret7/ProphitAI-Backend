from fastapi import APIRouter
from app.api.controller.alts import (
    get_fund_final_positions_controller,
    get_fund_table_controller,
    get_fund_sector_concentration_controller,
    get_fund_industry_concentration_controller,
    get_fund_sub_industry_concentration_controller,
    get_fund_industry_positions_controller,
    get_fund_sub_industry_positions_controller,
    get_fund_correlation_matrix_controller,
)

router = APIRouter()

@router.get("/alts/fund/{fund_name}/data")
async def get_fund_final_positions(fund_name: str):
    """
    Get fund performance data by fund name
    
    Args:
        fund_name: Name of the fund to retrieve final positions for
    """
    return await get_fund_final_positions_controller(fund_name=fund_name)

@router.get("/alts/funds")
async def get_funds():
    """
    Get all funds
    """
    return await get_fund_table_controller()

@router.get("/alts/fund/{fund_name}/sectors")
async def get_fund_sectors(fund_name: str):
    """
    Get fund sector concentration as percentage allocations.

    Returns a dictionary mapping sector names to allocation percentages.
    """
    return await get_fund_sector_concentration_controller(fund_name=fund_name)

@router.get("/alts/fund/{fund_name}/industries")
async def get_fund_industries(fund_name: str):
    """
    Get fund industry concentration as percentage allocations.

    Returns a dictionary mapping industry names to allocation percentages.
    """
    return await get_fund_industry_concentration_controller(fund_name=fund_name)

@router.get("/alts/fund/{fund_name}/sub-industries")
async def get_fund_sub_industries(fund_name: str):
    """
    Get fund sub-industry concentration as percentage allocations.

    Returns a dictionary mapping sub-industry names to allocation percentages.
    """
    return await get_fund_sub_industry_concentration_controller(fund_name=fund_name)

@router.get("/alts/fund/{fund_name}/industries/positions")
async def get_fund_industry_positions(fund_name: str):
    """
    Get fund industry concentration with long/short position breakdown.

    Returns a dictionary mapping industry names to position breakdowns
    (total, long, short, net percentages).
    """
    return await get_fund_industry_positions_controller(fund_name=fund_name)

@router.get("/alts/fund/{fund_name}/sub-industries/positions")
async def get_fund_sub_industry_positions(fund_name: str):
    """
    Get fund sub-industry concentration with long/short position breakdown.

    Returns a dictionary mapping sub-industry names to position breakdowns
    (total, long, short, net percentages).
    """
    return await get_fund_sub_industry_positions_controller(fund_name=fund_name)

@router.get("/alts/fund/{fund_name}/correlation")
async def get_fund_correlation_matrix(fund_name: str):
    """
    Get fund correlation matrix for all holdings.

    Calculates pairwise correlations using price returns over the default lookback period.

    Returns:
        - matrix: Full correlation matrix (dict of dicts)
        - pairs: List of pairwise correlations sorted by absolute value
        - metadata: Information about the calculation (tickers, date range, etc.)
    """
    return await get_fund_correlation_matrix_controller(fund_name=fund_name) 