from fastapi import APIRouter, Query
from backend.src.api.controller.prophit_alts_controller import (
    get_fund_final_positions_controller,
    get_fund_landing_page_metrics_controller
)

router = APIRouter()

@router.get("/fund/{fund_name}/final-positions")
async def get_fund_final_positions(fund_name: str):
    """
    Get fund final positions by fund name
    
    Args:
        fund_name: Name of the fund to retrieve final positions for
    """
    return await get_fund_final_positions_controller(fund_name=fund_name)

@router.get("/fund/{fund_name}/metrics")
async def get_fund_landing_page_metrics(fund_name: str):
    """
    Get fund landing page metrics including performance and risk metrics
    
    Args:
        fund_name: Name of the fund to retrieve metrics for
        
    Returns:
        Dict with:
        - ytd_return: Year-to-date return (%)
        - gross_exposure: Sum of absolute position values (%)
        - net_exposure: Net long minus short exposure (%)
        - sharpe_ratio: Risk-adjusted return ratio
        - sortino_ratio: Downside risk-adjusted return ratio
        - max_drawdown: Maximum peak-to-trough decline (%)
        - beta: Market correlation vs SPY
        - var_95: 95% confidence Value at Risk (%)
    """
    return await get_fund_landing_page_metrics_controller(fund_name=fund_name)
