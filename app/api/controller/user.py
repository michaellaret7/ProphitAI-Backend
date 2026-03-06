import logging
from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.repositories.user.account import (
    get_all_user_data_by_clerk_id,
    add_user,
    update_user_by_clerk_id,
    delete_user_by_clerk_id,
)
from app.api.auth.clerk import get_clerk_client
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors

logger = logging.getLogger(__name__)


def _format_user_response(user_data: dict, clerk_id: str) -> Dict[str, Any]:
    """Format user data for API response."""
    portfolios = [
        {
            "portfolioId": p.get("portfolio_id"),
            "name": p.get("name"),
            "isCurrent": p.get("is_current"),
            "isDiscretionary": p.get("is_discretionary"),
        }
        for p in user_data.get("portfolios", [])
    ]

    return ok_envelope(
        message="User data retrieved successfully",
        kind="users#user",
        resource_id=user_data.get("id"),
        self_link=f"/api/user",
        payload={
            "id": user_data.get("id"),
            "clerkId": user_data.get("clerk_id"),
            "email": user_data.get("email"),
            "firstName": user_data.get("first_name"),
            "lastName": user_data.get("last_name"),
            "broker": user_data.get("broker"),
            "snaptradeUserId": user_data.get("snaptrade_user_id"),
            "snaptradeAccountId": user_data.get("snaptrade_account_id"),
            "portfolios": portfolios,
        },
    )


@handle_controller_errors
async def get_user_by_clerk_controller(*, clerk_id: str) -> Dict[str, Any]:
    """
    Get user by Clerk ID with JIT provisioning.

    If the user doesn't exist locally (e.g. webhook didn't fire in local dev),
    fetch their info from Clerk's API and create them on the fly.
    """
    if not clerk_id:
        raise ValueError("clerkId is required")

    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

    if not user_data:
        # Reason: JIT provisioning — covers local dev where Clerk webhooks can't reach localhost
        logger.info(f"User not found for clerk_id={clerk_id}, provisioning from Clerk API")
        clerk = get_clerk_client()
        clerk_user = clerk.users.get(user_id=clerk_id)

        email = clerk_user.email_addresses[0].email_address
        add_user(
            email=email,
            first_name=clerk_user.first_name or "",
            last_name=clerk_user.last_name or "",
            clerk_id=clerk_id,
        )
        user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

        if not user_data:
            raise HTTPException(status_code=500, detail="Failed to provision user")

    return _format_user_response(user_data, clerk_id)


@handle_controller_errors
async def update_user_controller(
    *,
    clerk_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Update user by clerk_id."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    if first_name is None and last_name is None:
        raise ValueError("No fields provided to update")

    updated = update_user_by_clerk_id(
        clerk_id=clerk_id,
        first_name=first_name,
        last_name=last_name,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
    return _format_user_response(user_data, clerk_id)


@handle_controller_errors
async def delete_user_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Delete user by clerk_id."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    deleted = delete_user_by_clerk_id(clerk_id=clerk_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return ok_envelope(
        message="User deleted successfully",
        kind="users#user",
        resource_id=clerk_id,
        self_link="/api/user",
        payload={}
    )
