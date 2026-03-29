from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from prophitai_api.controllers.user import (
    get_user_by_clerk_controller,
    update_user_controller,
    delete_user_controller,
)
from prophitai_api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["User Management"])


class UpdateUserRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None


@router.get("/user")
async def get_user(clerk_id: str = Depends(get_clerk_user_id)):
    """Get current user data. Auto-provisions from Clerk if not in local DB."""
    return await get_user_by_clerk_controller(clerk_id=clerk_id)


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
