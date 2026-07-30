"""
Tests Router
Handles test/assessment operations
"""
import logging
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/test", tags=["Tests"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class TestCreateRequest(BaseModel):
    user_id: str
    assessment_id: Optional[int] = None
    trial1: float
    trial2: float
    trial3: float
    hand: str  # "Left" or "Right"
    posture: str
    device_id: Optional[str] = None


class TestResponse(BaseModel):
    id: int
    user_id: str
    assessment_id: Optional[int]
    trial1: float
    trial2: float
    trial3: float
    average: float
    hand: str
    posture: str
    device_id: Optional[str]
    created_at: str


# ============================================================================
# Test Endpoints
# ============================================================================

@router.get("/user/{user_id}", response_model=List[dict])
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


@router.get("/assessment/{assessment_id}", response_model=List[dict])
async def get_assessment_tests(assessment_id: int):
    """
    Get all tests for an assessment
    """
    try:
        log_request({"assessment_id": assessment_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get tests for assessment
        result = supabase.table("tests").select("*").eq("assessment_id", assessment_id).order("created_at", desc=True).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"assessment_id": assessment_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assessment tests"
        )


@router.get("/hands/{user_id}", response_model=dict)
async def get_hands_values(user_id: str):
    """
    Get latest test values for left and right hands
    Returns format: {"Left": [...], "Right": [...]}
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get latest test for left hand
        left_result = supabase.table("tests").select("*").eq("user_id", user_id).eq("hand", "Left").order("created_at", desc=True).limit(1).execute()
        
        # Get latest test for right hand
        right_result = supabase.table("tests").select("*").eq("user_id", user_id).eq("hand", "Right").order("created_at", desc=True).limit(1).execute()
        
        result = {
            "Left": left_result.data if left_result.data else [],
            "Right": right_result.data if right_result.data else []
        }
        
        log_response(result, logger)
        
        return result
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hands values"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_test(test_data: TestCreateRequest):
    """
    Create a new test/reading
    """
    try:
        log_request(test_data.dict(), logger)
        
        supabase = get_supabase_client()
        
        # Calculate average
        average = round((test_data.trial1 + test_data.trial2 + test_data.trial3) / 3, 2)
        
        # Prepare test data
        test_dict = {
            "user_id": test_data.user_id,
            "assessment_id": test_data.assessment_id,
            "trial1": test_data.trial1,
            "trial2": test_data.trial2,
            "trial3": test_data.trial3,
            "average": average,
            "hand": test_data.hand,
            "posture": test_data.posture,
            "device_id": test_data.device_id,
            "created_at": "now()"
        }
        
        # Insert test
        result = supabase.table("tests").insert(test_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create test"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"test_data": test_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test"
        )


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(test_id: int):
    """
    Delete a test
    """
    try:
        log_request({"test_id": test_id}, logger)
        
        supabase = get_supabase_client()
        
        # Delete test
        result = supabase.table("tests").delete().eq("id", test_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"test_id": test_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete test"
        )