from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.repositories.user_data import get_all_user_data, add_user
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

async def get_user_portfolio_list_controller(email: str) -> Dict[str, Any]:
    """
    Controller to handle user portfolio list retrieval
    """
    try:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        user_data = get_all_user_data(email=email)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        portfolios = user_data.get('portfolios', [])
        # Convert to camelCase keys for response
        portfolios = [{
            "name": p.get("name"),
            "portfolioId": p.get("portfolio_id"),
            "isCurrent": p.get("is_current")
        } for p in portfolios]
        
        counts = {
            'currentItemCount': len(portfolios),
            'itemsPerPage': len(portfolios),
            'startIndex': 1,
            'totalItems': len(portfolios),
        }
        return ok_envelope(
            message="User portfolio list retrieved successfully",
            kind="users#portfolios",
            resource_id=user_data.get('id') if isinstance(user_data, dict) else None,
            self_link=f"/api/user/portfolios?email={email}",
            counts=counts,
            payload=portfolios,
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
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
    # Create or retrieve the user
    add_user(email=email, first_name=first_name, last_name=last_name, clerk_id=clerk_id)
    # Fetch fresh data with a new session to avoid detached instance issues
    data = get_all_user_data(email=email)
    if not data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    filtered_companies = [{"id": c.get("id")} for c in data.get("companies", [])]

    return ok_envelope(
        message="User created successfully",
        kind="users#user",
        resource_id=data.get("id"),
        self_link=f"/api/user/data?email={email}",
        payload={
            "email": data.get("email"),
            "firstName": data.get("first_name"),
            "lastName": data.get("last_name"),
            "dateCreated": data.get("creation_date"),
            "companies": filtered_companies,
        },
        status=201,
    )