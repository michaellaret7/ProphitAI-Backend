from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.api.controller.user import (
    get_user_by_clerk_controller,
    update_user_controller,
    delete_user_controller,
)
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["User Management"])


class UpdateUserRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None


@router.get("/user")
async def get_user(
    clerk_id: str = Depends(get_clerk_user_id),
    email: Optional[EmailStr] = Query(None, description="Email (required for first login)"),
    firstName: Optional[str] = Query(None),
    lastName: Optional[str] = Query(None),
):
    """
    Get current user. Creates user in DB on first login.

    On first login, pass email/firstName/lastName from Clerk.
    Subsequent logins only need the JWT (clerk_id extracted automatically).
    """
    return await get_user_by_clerk_controller(
        clerk_id=clerk_id,
        email=email,
        first_name=firstName,
        last_name=lastName,
    )


@router.patch("/user")
async def update_user(
    body: UpdateUserRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Update current user's profile."""
    return await update_user_controller(
        clerk_id=clerk_id,
        first_name=body.firstName,
        last_name=body.lastName,
    )


@router.delete("/user")
async def delete_user(clerk_id: str = Depends(get_clerk_user_id)):
    """Delete current user's account."""
    return await delete_user_controller(clerk_id=clerk_id)
