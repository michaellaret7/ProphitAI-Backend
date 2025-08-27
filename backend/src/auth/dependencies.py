from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict, Any
from backend.src.repositories.user_data import get_user_basic_info, get_all_user_data

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user
    
    TODO: Implement proper session/JWT validation
    Currently returns a placeholder for development
    """
    
    # TODO: Extract session token or JWT from request
    # Examples of where auth tokens could be stored:
    # - Cookie: request.cookies.get("session_token")  
    # - Authorization header: request.headers.get("authorization")
    # - Custom header: request.headers.get("x-auth-token")
    
    session_token = request.cookies.get("auth_session")
    auth_header = request.headers.get("authorization")
    
    if not session_token and not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no session or auth token provided"
        )
    
    # TODO: Validate session/JWT token here
    # For now, we'll use a placeholder implementation
    
    try:
        # TODO: Replace this with actual token validation
        # This is a placeholder - in real implementation you would:
        # 1. Validate the token/session
        # 2. Extract user identifier from validated token
        # 3. Query user from database
        
        # Placeholder: For development, we'll look for a test user
        # In production, you'd extract user_id/email from validated token
        test_user_email = "test@example.com"  # TODO: Remove this placeholder
        
        user_data = get_all_user_data(email=test_user_email)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user_data
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error"
        )

async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Dependency to optionally get the current user
    Returns None if not authenticated instead of raising an exception
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

def get_current_user_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency to get just the current user's ID
    Useful when you only need the user ID for queries
    """
    return current_user["id"]

def get_current_user_email(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    Dependency to get just the current user's email
    Useful when you only need the email for queries  
    """
    return current_user["email"]
