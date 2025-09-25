from fastapi import APIRouter, Query
from app.api.controller.portfolio_controller import get_user_portfolio_list_controller

router = APIRouter()

@router.get("/user/portfolios")
async def get_user_portfolio_list(email: str = Query(None, description="User's email address")):
    """
    Get user portfolio list by email
    
    Email must be provided.
    """
    return await get_user_portfolio_list_controller(email=email)

