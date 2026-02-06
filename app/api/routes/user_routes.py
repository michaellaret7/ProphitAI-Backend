from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.api.controller.user import (
    get_user_by_clerk_controller,
    update_user_controller,
    delete_user_controller,
    set_user_role_controller,
)
from app.api.auth.clerk import get_clerk_user_id

router = APIRouter(tags=["User Management"])


class UpdateUserRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None


class SetUserRoleRequest(BaseModel):
    role: str


@router.get("/user")
async def get_user(clerk_id: str = Depends(get_clerk_user_id)):
    """Get current user data."""
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


@router.post("/user/role")
async def set_user_role(
    body: SetUserRoleRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Set current user's role during onboarding. Can only be called once."""
    return await set_user_role_controller(clerk_id=clerk_id, role=body.role)


@router.delete("/user")
async def delete_user(clerk_id: str = Depends(get_clerk_user_id)):
    """Delete current user's account."""
    return await delete_user_controller(clerk_id=clerk_id)
