from fastapi import APIRouter
from app.api.controller.prophit_alts_controller import (
    get_fund_final_positions_controller
)

router = APIRouter()

@router.get("/prophit-alts/fund/{fund_name}/performance-data")
async def get_fund_final_positions(fund_name: str):
    """
    Get fund performance data by fund name
    
    Args:
        fund_name: Name of the fund to retrieve final positions for
    """
    return await get_fund_final_positions_controller(fund_name=fund_name)