from fastapi import HTTPException
from typing import Optional, Dict, Any
from backend.src.repositories.user_data import get_all_user_data

async def get_user_data_controller(
    email: Optional[str] = None, 
    user_id: Optional[str] = None, 
    workos_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Controller to handle user data retrieval
    """
    try:
        user_data = get_all_user_data(email=email, user_id=user_id, workos_id=workos_id)
        
        if not user_data:
            raise HTTPException(
                status_code=404, 
                detail="User not found with provided identifier"
            )
        
        return {
            "success": True,
            "data": user_data,
            "message": "User data retrieved successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
