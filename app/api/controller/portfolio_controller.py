from fastapi import HTTPException
from typing import Dict, Any
from app.repositories.portfolio_data import list_portfolios
from app.repositories.user_data import get_all_user_data
from app.api.response_envelope import ok_envelope

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