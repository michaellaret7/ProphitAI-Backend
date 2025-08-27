from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from .config import workos_client, REDIRECT_URI
from .models import LoginResponse, UserProfile
from backend.src.repositories.user_data import get_user_basic_info, add_user, update_user_workos_id
import uuid

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/login")
async def login():
    """Initiate the SSO login flow"""
    # Using WorkOS test organization for development
    # TODO: Replace with dynamic organization lookup based on company domain
    organization_id = "org_test_idp"
    
    # Generate the WorkOS SSO authorization URL
    authorization_url = workos_client.sso.get_authorization_url(
        organization_id=organization_id,
        redirect_uri=REDIRECT_URI
    )
    
    # Redirect the user to the SSO authorization URL
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def callback(request: Request):
    """Handle the OAuth callback from WorkOS"""
    # Parse the 'code' query parameter from the redirect URL
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    try:
        # Exchange the code for a profile and token via WorkOS
        profile_and_token = workos_client.sso.get_profile_and_token(code)
        profile = profile_and_token.profile
        
        # Verify the login is for the expected organization (security check)
        expected_org = "org_test_idp"
        if profile.organization_id != expected_org:
            raise HTTPException(status_code=401, detail="Unauthorized organization")
        
        # Check if user exists in our database
        existing_user = get_user_basic_info(email=profile.email)
        
        if existing_user:
            update_user_workos_id(profile.email, profile.id)
            user_data = existing_user
        else:
            # User doesn't exist - create new user
            add_user(
                email=profile.email,
                first_name=profile.first_name or "",
                last_name=profile.last_name or "",
                workos_id=profile.id,
            )
            # Get the newly created user
            user_data = get_user_basic_info(email=profile.email)
        
        if not user_data:
            raise HTTPException(status_code=500, detail="Failed to create or retrieve user")
        
        # TODO: Create session/JWT for user authentication
        # For now, we'll just redirect to the frontend dashboard
        
        # Redirect to frontend dashboard
        frontend_dashboard_url = "http://localhost:5173/dashboard"
        return RedirectResponse(url=frontend_dashboard_url)
        
    except Exception as e:
        print(f"Error during SSO callback: {e}")
        # Redirect back to login on error
        return RedirectResponse(url="/auth/login")

@router.get("/user-info")  
async def get_user_info(request: Request):
    """Get current user information - placeholder for testing"""
    # TODO: Implement proper session/JWT validation
    # This is a placeholder endpoint for testing
    return {"message": "User info endpoint - TODO: implement session management"}
