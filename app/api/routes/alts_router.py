from fastapi import APIRouter
from app.api.controller.alts import (
    get_fund_final_positions_controller,
    get_fund_table_controller
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