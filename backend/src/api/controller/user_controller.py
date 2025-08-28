from fastapi import HTTPException
from typing import Optional, Dict, Any
from backend.src.repositories.user_data import get_all_user_data

async def get_user_data_controller(email: str) -> Dict[str, Any]:
    """
    Controller to handle user data retrieval
    """
    try:
        user_data = get_all_user_data(email=email)
        
        if not user_data:
            raise HTTPException(
                status_code=404, 
                detail="User not found with provided identifier"
            )
        
        return {
            "status": 200,
            "data": user_data,
            "message": "User data retrieved successfully"
        }
    
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without modification
        raise
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )