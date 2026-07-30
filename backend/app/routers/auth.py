"""
Authentication Router
Handles user login, registration, and authentication using Supabase
"""
import os
import sys
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get Supabase client for authentication"""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        options=ClientOptions(flow_type="pkce")
    )


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str
    phone: Optional[str] = None
    user_type: str = "Patient"  # "Patient" or "Specialist"


class LoginResponse(BaseModel):
    id: str
    email: str
    name: str
    user_type: str
    access_token: str
    refresh_token: str


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=dict)
async def login(request: LoginRequest):
    """
    Patient login endpoint
    Returns user data and sets session cookie
    """
    try:
        log_request({"email": request.email}, logger)
        
        supabase = get_supabase_client()
        
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = response.user
        session = response.session
        
        # Get user profile from database
        profile = None
        try:
            profile_result = supabase.table("profiles").select("*").eq("id", user.id).execute()
            if profile_result.data:
                profile = profile_result.data[0]
        except Exception as e:
            logger.warning(f"Could not fetch user profile: {e}")
        
        # Build response
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": profile.get("name") if profile else user.email,
            "user_type": profile.get("user_type", "Patient") if profile else "Patient",
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
        
        log_response(user_data, logger)
        
        # Return user data (Flutter app expects this format)
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"endpoint": "login", "email": request.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/login-specialist", response_model=dict)
async def login_specialist(request: LoginRequest):
    """
    Specialist login endpoint
    Returns user data and sets session cookie
    """
    try:
        log_request({"email": request.email}, logger)
        
        supabase = get_supabase_client()
        
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = response.user
        session = response.session
        
        # Get user profile from database
        profile = None
        try:
            profile_result = supabase.table("profiles").select("*").eq("id", user.id).execute()
            if profile_result.data:
                profile = profile_result.data[0]
                
                # Check if user is actually a specialist
                if profile.get("user_type") != "Specialist":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="This account is not registered as a specialist"
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Could not fetch user profile: {e}")
        
        # Build response
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": profile.get("name") if profile else user.email,
            "user_type": "Specialist",
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
        
        log_response(user_data, logger)
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"endpoint": "login_specialist", "email": request.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    User registration endpoint
    Creates new user in Supabase Auth and profiles table
    """
    try:
        log_request({
            "email": request.email,
            "name": request.name,
            "user_type": request.user_type
        }, logger)
        
        supabase = get_supabase_client()
        
        # Create user in Supabase Auth
        try:
            response = supabase.auth.sign_up({
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "name": request.name,
                        "user_type": request.user_type
                    }
                }
            })
        except Exception as auth_error:
            # Supabase throws an error if user already exists
            error_str = str(auth_error).lower()
            if "already" in error_str or "exists" in error_str or "duplicate" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email already exists. Please login instead."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(auth_error)}"
            )
        
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please try again."
            )
        
        user = response.user
        session = response.session
        
        # Create profile in database
        try:
            profile_data = {
                "id": user.id,
                "email": request.email,
                "name": request.name,
                "phone": request.phone,
                "user_type": request.user_type,
                "created_at": "now()"
            }
            supabase.table("profiles").insert(profile_data).execute()
        except Exception as e:
            logger.warning(f"Could not create profile: {e}")
        
        # Build response
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": request.name,
            "user_type": request.user_type,
            "access_token": session.access_token if session else "",
            "refresh_token": session.refresh_token if session else "",
        }
        
        log_response(user_data, logger)
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"endpoint": "register", "email": request.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: dict):
    """
    Send password reset email
    """
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        log_request({"email": email}, logger)
        
        supabase = get_supabase_client()
        
        # Send password reset email
        supabase.auth.reset_password_email(email)
        
        return {"message": "Password reset email sent successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"endpoint": "forgot_password"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )


@router.post("/reset-password", response_model=dict)
async def reset_password(request: dict):
    """
    Reset password with token
    """
    try:
        token = request.get("token")
        new_password = request.get("new_password")
        
        if not token or not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token and new password are required"
            )
        
        log_request({"token": token}, logger)
        
        supabase = get_supabase_client()
        
        # Reset password
        supabase.auth.reset_password_email(new_password)
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"endpoint": "reset_password"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/logout", response_model=dict)
async def logout():
    """
    Logout endpoint - invalidates the session
    """
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        log_error(e, logger, {"endpoint": "logout"})
        return {"message": "Logged out successfully"}