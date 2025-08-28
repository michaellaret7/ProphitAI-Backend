from fastapi import APIRouter, Query
from backend.src.api.controller.user_controller import get_user_data_controller

router = APIRouter()

@router.get("/data")
async def get_user_data(email: str = Query(None, description="User's email address")):
    """
    Get complete user data by email
    
    Email must be provided.
    """
    return await get_user_data_controller(email=email)