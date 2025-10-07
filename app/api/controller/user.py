from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.repositories.user_data import (
    get_all_user_data,
    get_all_user_data_by_clerk_id,
    add_user,
    update_user_fields,
    delete_user_by_clerk_id,
    assign_user_to_company_by_email,
)
from app.api.response_envelope import ok_envelope

async def get_user_data_controller(email: str) -> Dict[str, Any]:
    """
    Controller to handle user data retrieval
    """
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        user_data = get_all_user_data(email=email)

        if not user_data:
            raise HTTPException(
                status_code=404, 
                detail="User not found with provided identifier"
            )
        
        # Filter companies to only include company id and remove portfolios
        filtered_companies = [{"id": company["id"]} for company in user_data.get("companies", [])]

        # Convert to camelCase keys for response
        filtered_data = {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "firstName": user_data.get("first_name"),
            "lastName": user_data.get("last_name"),
            "companies": filtered_companies
        }
        
        return ok_envelope(
            message="User data retrieved successfully",
            kind="users#user",
            resource_id=filtered_data.get("id"),
            self_link=f"/api/user/email?email={email}",
            payload={
                "email": filtered_data.get("email"),
                "firstName": filtered_data.get("firstName"),
                "lastName": filtered_data.get("lastName"),
                "companies": filtered_data.get("companies", []),
            }
        )
    
    except HTTPException:
        raise
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

async def get_user_by_clerk_controller(
    *,
    clerk_id: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch user by Clerk ID. If not found, create using provided Clerk user info.
    """
    try:
        if not clerk_id:
            raise HTTPException(status_code=400, detail="clerkId is required")

        user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

        # Create if missing, using Clerk-provided info
        if not user_data:
            # First-login patch: if email exists without clerk_id, patch it
            if email:
                try:
                    # Attempt to update a user with this email to set clerk_id
                    updated = update_user_fields(email=email, clerk_id=clerk_id)
                    if updated:
                        user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
                except Exception:
                    # If update fails, proceed to create
                    user_data = None
            # If still missing, create fresh
            if not user_data:
                if not email:
                    raise HTTPException(status_code=400, detail="email is required to create user")
                created = add_user(
                    email=email,
                    first_name=first_name or "",
                    last_name=last_name or "",
                    clerk_id=clerk_id,
                )
                if not created:
                    raise HTTPException(status_code=500, detail="Failed to create user")
                # Assign created user to ProphitAI with admin role
                try:
                    assign_user_to_company_by_email(email=email, company_name='ProphitAI', role='admin')
                except Exception:
                    pass
                user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)

        filtered_companies = [{"id": company["id"]} for company in user_data.get("companies", [])]

        filtered_data = {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "firstName": user_data.get("first_name"),
            "lastName": user_data.get("last_name"),
            "companies": filtered_companies,
        }

        return ok_envelope(
            message="User data retrieved successfully",
            kind="users#user",
            resource_id=filtered_data.get("id"),
            self_link=f"/api/user?clerkId={clerk_id}",
            payload={
                "email": filtered_data.get("email"),
                "firstName": filtered_data.get("firstName"),
                "lastName": filtered_data.get("lastName"),
                "companies": filtered_data.get("companies", []),
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def delete_user_controller(*, clerk_id: str) -> Dict[str, Any]:
    try:
        if not clerk_id:
            raise HTTPException(status_code=400, detail="clerkId is required")
        deleted = delete_user_by_clerk_id(clerk_id=clerk_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        return ok_envelope(
            message="User deleted successfully",
            kind="users#user",
            resource_id=clerk_id,
            self_link=f"/api/user?clerkId={clerk_id}",
            payload={}
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def create_user_controller(
    *,
    email: str,
    first_name: str,
    last_name: str,
    clerk_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = add_user(email=email, first_name=first_name, last_name=last_name, clerk_id=clerk_id)
    try:
        assign_user_to_company_by_email(email=email, company_name='ProphitAI', role='admin')
    except Exception:
        pass

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Return FE-provided body info without re-fetching
    resource_id = clerk_id or email
    payload = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
    }
    if clerk_id is not None:
        payload["clerkId"] = clerk_id

    return ok_envelope(
        message="User created successfully",
        kind="users#user",
        resource_id=resource_id,
        self_link=f"/api/user",
        payload=payload,
        status=201,
    )

async def update_user_controller(
    *,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    clerk_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        # Ensure at least one field to update is provided
        if all(v is None for v in [first_name, last_name, clerk_id]):
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # Attempt update
        updated = update_user_fields(
            email=email,
            first_name=first_name,
            last_name=last_name,
            clerk_id=clerk_id,
        )

        if not updated:
            raise HTTPException(status_code=404, detail="User not found")

        # Return FE-provided body info without re-fetching
        resource_id = clerk_id or email
        payload = {"email": email}
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if clerk_id is not None:
            payload["clerkId"] = clerk_id

        return ok_envelope(
            message="User updated successfully",
            kind="users#user",
            resource_id=resource_id,
            self_link=f"/api/user",
            payload=payload,
            status=200,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

