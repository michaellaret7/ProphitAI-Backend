from fastapi import APIRouter, Query
from typing import Optional
from backend.src.api.controller.user_controller import get_user_data_controller

router = APIRouter()

@router.get("/data")
async def get_user_data(
    email: Optional[str] = Query(None, description="User's email address"),
    user_id: Optional[str] = Query(None, description="User's UUID"),
    workos_id: Optional[str] = Query(None, description="User's WorkOS ID")
):
    """
    Get complete user data by email, user_id, or workos_id
    
    At least one identifier must be provided.
    """
    return await get_user_data_controller(email=email, user_id=user_id, workos_id=workos_id)
