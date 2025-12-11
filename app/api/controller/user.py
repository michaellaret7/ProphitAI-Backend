from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.repositories.user_data import (
    get_all_user_data_by_clerk_id,
    add_user,
    update_user_fields,
    update_user_by_clerk_id,
    delete_user_by_clerk_id,
    assign_user_to_company_by_email,
)
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


def _format_user_response(user_data: dict, clerk_id: str) -> Dict[str, Any]:
    """Format user data for API response."""
    # Format companies with full info
    companies = [
        {
            "id": c["id"],
            "name": c.get("name"),
            "role": c.get("user_role"),
        }
        for c in user_data.get("companies", [])
    ]

    # Format portfolios
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
            "companies": companies,
            "portfolios": portfolios,
        },
    )


@handle_controller_errors
async def get_user_by_clerk_controller(
    *,
    clerk_id: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get user by Clerk ID. Creates user on first login if email provided.
    """
    if not clerk_id:
        raise ValueError("clerkId is required")

    # Try to find existing user
    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

    # First login - create user
    if not user_data:
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email required for first login. Pass email from Clerk."
            )

        # Check if email exists without clerk_id (link existing user)
        try:
            updated = update_user_fields(email=email, clerk_id=clerk_id)
            if updated:
                user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
        except Exception:
            pass

        # Still no user - create new
        if not user_data:
            created = add_user(
                email=email,
                first_name=first_name or "",
                last_name=last_name or "",
                clerk_id=clerk_id,
            )
            if not created:
                raise HTTPException(status_code=500, detail="Failed to create user")

            # Auto-assign to Default Company with member role
            try:
                assign_user_to_company_by_email(email=email, company_name='Default Company', role='member')
            except Exception:
                pass

            user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

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


# Legacy function kept for compatibility
@handle_controller_errors
async def get_user_data_controller(email: str) -> Dict[str, Any]:
    """Get user by email (legacy)."""
    raise HTTPException(status_code=410, detail="Use /api/user with JWT instead")
