from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.api.controller.user_controller import (
    get_user_data_controller,
    create_user_controller,
    update_user_controller,
)

router = APIRouter()

class CreateUserRequest(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    clerkId: Optional[str] = None

class UpdateUserRequest(BaseModel):
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    clerkId: Optional[str] = None

@router.get("/user/email")
async def get_user_data_by_email(email: str = Query(None, description="User's email address")):
    """
    Get complete user data by email
    
    Email must be provided.
    """
    return await get_user_data_controller(email=email)

@router.get("/user")
async def get_user_data(clerk_id: str = Query(None, description="User's clerk id")):
    """
    Get complete user data by clerk id
    
    Clerk id must be provided.
    """
    return await get_user_data_controller(clerk_id=clerk_id)

@router.post("/user", status_code=201)
async def create_user(body: CreateUserRequest):
    return await create_user_controller(
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
        clerk_id=body.clerkId,
    )

@router.patch("/user")
async def patch_user(body: UpdateUserRequest):
    return await update_user_controller(
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
        clerk_id=body.clerkId,
    )

# @router.delete("/user")
# async def delete_user(clerk_id: str = Query(None, description="User's clerk id")):
#     return await delete_user_controller(clerk_id=clerk_id)
