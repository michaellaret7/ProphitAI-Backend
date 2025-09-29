from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.repositories.user_data import get_all_user_data, add_user, update_user_fields
from app.api.response_envelope import ok_envelope

async def get_user_data_controller(email: str) -> Dict[str, Any]:
    """
    Controller to handle user data retrieval
    """
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        user_data = get_all_user_data(email=email)

        # If user data is missing, cler id is null and we need to patch the user account 
        #TODO: How to get the body from the request 
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
            self_link=f"/api/user/data?email={email}",
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

async def create_user_controller(
    *,
    email: str,
    first_name: str,
    last_name: str,
    clerk_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = add_user(email=email, first_name=first_name, last_name=last_name, clerk_id=clerk_id)

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {"status": 201, "message": "User created successfully"}

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

        return {"status": 200, "message": "User updated successfully"}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# async def delete_user_controller(clerk_id: str) -> Dict[str, Any]:
#     deleted = delete_user(clerk_id=clerk_id)
#     if not deleted:
#         raise HTTPException(status_code=404, detail="User not found")
#     return {"status": 200, "message": "User deleted successfully"}