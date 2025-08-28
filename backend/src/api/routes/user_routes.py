from fastapi import APIRouter, Query
from backend.src.api.controller.user_controller import get_user_data_controller, get_user_basic_info_controller

router = APIRouter()

@router.get("/data")
async def get_user_data(email: str = Query(None, description="User's email address")):
    """
    Get complete user data by email, user_id, or workos_id
    
    At least one identifier must be provided.
    """
    return await get_user_data_controller(email=email)

@router.get("/basic")
async def get_user_basic_info(email: str = Query(None, description="User's email address")):
    """
    Get basic user info (id, workos_id, email, first_name, last_name) by email
    
    Email must be provided.
    """
    return await get_user_basic_info_controller(email=email)
