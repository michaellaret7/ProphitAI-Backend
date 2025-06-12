from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response
from .config import workos, REDIRECT_URI, COOKIE_PASSWORD
from .dependencies import get_current_user, get_optional_user
from backend.src.utils.database import get_cursor
import psycopg2
import psycopg2.sql

router = APIRouter(prefix="/auth", tags=["authentication"])

def upsert_user(user_data):
    """
    Inserts a new user into the database, or updates them if they already exist.
    """
    db_name = "user_data"
    schema_name = "public"
    table_name = "users"

    query = psycopg2.sql.SQL("""
        INSERT INTO {}.{} (id, email, first_name, last_name, email_verified, updated_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email_verified = EXCLUDED.email_verified,
            updated_at = CURRENT_TIMESTAMP;
    """).format(psycopg2.sql.Identifier(schema_name), psycopg2.sql.Identifier(table_name))

    try:
        with get_cursor(dbname=db_name) as cursor:
            cursor.execute(query, (
                user_data.id,
                user_data.email,
                user_data.first_name,
                user_data.last_name,
                user_data.email_verified
            ))
    except psycopg2.Error as e:
        print(f"Database error during user upsert: {e}")
        # Depending on the desired behavior, you might want to raise an exception here
        # For now, we'll just log it and continue.
    except Exception as e:
        print(f"An unexpected error occurred during user upsert: {e}")

@router.get("/login")
async def login():
    """Initiate the login flow"""
    authorization_url = workos.user_management.get_authorization_url(
        provider="authkit",
        redirect_uri=REDIRECT_URI
    )
    return RedirectResponse(url=authorization_url)

@router.get("/callback")
async def callback(code: str):
    """Handle the OAuth callback"""
    try:
        # Exchange code for user session
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
            session={
                "seal_session": True,
                "cookie_password": COOKIE_PASSWORD
            }
        )
        
        # Upsert user to our local database
        upsert_user(auth_response.user)
        
        # Create response and set session cookie
        response = RedirectResponse(url="http://localhost:5173/dashboard")
        response.set_cookie(
            key="wos_session",
            value=auth_response.sealed_session,
            secure=True,
            httponly=True,
            samesite="lax"
        )
        
        return response
    except Exception as e:
        print(f"Error authenticating with code: {e}")
        return RedirectResponse(url="/auth/login")

@router.get("/logout")
async def logout(request: Request):
    """Log out the user"""
    session_cookie = request.cookies.get("wos_session")
    
    if session_cookie:
        try:
            session = workos.user_management.load_sealed_session(
                sealed_session=session_cookie,
                cookie_password=COOKIE_PASSWORD
            )
            logout_url = session.get_logout_url()
        except:
            logout_url = "http://localhost:5173"
    else:
        logout_url = "http://localhost:5173"
    
    response = RedirectResponse(url=logout_url)
    response.delete_cookie(key="wos_session")
    return response

@router.get("/user")
async def get_user(current_user=Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email_verified": current_user.email_verified
    }