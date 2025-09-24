from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.api.controller.user_controller import get_user_data_controller, get_user_portfolio_list_controller, create_user_controller

router = APIRouter()

class CreateUserRequest(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    clerkId: Optional[str] = None

@router.get("/user/data")
async def get_user_data(email: str = Query(None, description="User's email address")):
    """
    Get complete user data by email
    
    Email must be provided.
    """
    return await get_user_data_controller(email=email)

@router.post("/user", status_code=201)
async def create_user(body: CreateUserRequest):
    return await create_user_controller(
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
        clerk_id=body.clerkId,
    )

@router.get("/user/portfolios")
async def get_user_portfolio_list(email: str = Query(None, description="User's email address")):
    """
    Get user portfolio list by email
    
    Email must be provided.
    """
    return await get_user_portfolio_list_controller(email=email)

