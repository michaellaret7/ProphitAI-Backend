from functools import wraps
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from .config import workos, COOKIE_PASSWORD

async def get_current_user(request: Request):
    """Dependency to get the current authenticated user"""
    session_cookie = request.cookies.get("wos_session")
    
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        session = workos.user_management.load_sealed_session(
            sealed_session=session_cookie,
            cookie_password=COOKIE_PASSWORD
        )
        
        auth_response = session.authenticate()
        
        if auth_response.authenticated:
            return auth_response.user
        else:
            # Try to refresh the session
            result = session.refresh()
            if result.authenticated:
                # Note: In FastAPI, you'd need to handle cookie setting differently
                return result.user
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired"
                )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

async def get_optional_user(request: Request):
    """Dependency to optionally get the current user (doesn't fail if not authenticated)"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None