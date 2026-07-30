"""
Users Router
Handles user profile operations
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/user", tags=["Users"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    user_type: str
    age: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    created_at: Optional[str] = None


# ============================================================================
# User Endpoints
# ============================================================================

@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: str):
    """
    Get user profile by ID
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get user from profiles table
        result = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = result.data[0]
        log_response(user, logger)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )


@router.put("/{user_id}", response_model=dict)
async def update_user(user_id: str, user_data: UserUpdateRequest):
    """
    Update user profile
    """
    try:
        log_request({"user_id": user_id, "data": user_data.dict()}, logger)
        
        supabase = get_supabase_client()
        
        # Build update data (only include non-None values)
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        # Update user in profiles table
        result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.get("/{user_id}/assessments", response_model=list)
async def get_user_assessments(user_id: str):
    """
    Get all assessments for a user
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get assessments for user
        result = supabase.table("assessments").select("*").eq("user_id", user_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assessments"
        )


@router.get("/{user_id}/tests", response_model=list)
async def get_user_tests(user_id: str):
    """
    Get all tests for a user
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get tests for user
        result = supabase.table("tests").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tests"
        )


@router.get("/{user_id}/devices", response_model=list)
async def get_user_devices(user_id: str):
    """
    Get all devices associated with a user
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get devices for user
        result = supabase.table("devices").select("*").eq("user_id", user_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch devices"
        )