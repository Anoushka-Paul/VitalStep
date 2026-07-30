"""
Queue Router
Handles assessment queue operations
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/queue", tags=["Queue"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class QueueCreateRequest(BaseModel):
    user_id: int
    assessment_id: int
    device_id: int
    posture: str
    hand: str


class QueueResponse(BaseModel):
    id: int
    user_id: int
    assessment_id: int
    device_id: int
    posture: str
    hand: str
    status: str
    created_at: str


# ============================================================================
# Queue Endpoints
# ============================================================================

@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_queue(user_id: str):
    """
    Get all queue items for a user
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get queue items for user
        result = supabase.table("queue").select("*").eq("user_id", user_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queue"
        )


@router.get("/assessment/{assessment_id}", response_model=List[dict])
async def get_assessment_queue(assessment_id: str):
    """
    Get all queue items for an assessment
    """
    try:
        log_request({"assessment_id": assessment_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get queue items for assessment
        result = supabase.table("queue").select("*").eq("assessment_id", assessment_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"assessment_id": assessment_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assessment queue"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_queue_item(queue_data: QueueCreateRequest):
    """
    Create a new queue item
    """
    try:
        log_request(queue_data.dict(), logger)
        
        supabase = get_supabase_client()
        
        # Prepare queue data
        queue_dict = {
            "user_id": queue_data.user_id,
            "assessment_id": queue_data.assessment_id,
            "device_id": queue_data.device_id,
            "posture": queue_data.posture,
            "hand": queue_data.hand,
            "status": "pending",
            "created_at": "now()"
        }
        
        # Insert queue item
        result = supabase.table("queue").insert(queue_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create queue item"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"queue_data": queue_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create queue item"
        )


@router.delete("/{queue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_queue_item(queue_id: int):
    """
    Delete a queue item (cancel assessment)
    """
    try:
        log_request({"queue_id": queue_id}, logger)
        
        supabase = get_supabase_client()
        
        # Delete queue item
        result = supabase.table("queue").delete().eq("id", queue_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Queue item not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"queue_id": queue_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete queue item"
        )