"""
Remarks Router
Handles comments/remarks on assessments
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/remarks", tags=["Remarks"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class RemarkCreateRequest(BaseModel):
    assessment_id: int
    user_id: str
    comment: str
    remark_type: str = "general"  # "general", "specialist", "ai"


class RemarkResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: str
    comment: str
    remark_type: str
    created_at: str


# ============================================================================
# Remarks Endpoints
# ============================================================================

@router.get("/assessment/{assessment_id}", response_model=List[dict])
async def get_assessment_remarks(assessment_id: int):
    """
    Get all remarks for an assessment
    """
    try:
        log_request({"assessment_id": assessment_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get remarks for assessment
        result = supabase.table("remarks").select("*").eq("assessment_id", assessment_id).order("created_at", desc=False).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"assessment_id": assessment_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch remarks"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_remark(remark_data: RemarkCreateRequest):
    """
    Create a new remark/comment
    """
    try:
        log_request(remark_data.dict(), logger)
        
        supabase = get_supabase_client()
        
        # Prepare remark data
        remark_dict = {
            "assessment_id": remark_data.assessment_id,
            "user_id": remark_data.user_id,
            "comment": remark_data.comment,
            "remark_type": remark_data.remark_type,
            "created_at": "now()"
        }
        
        # Insert remark
        result = supabase.table("remarks").insert(remark_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create remark"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"remark_data": remark_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create remark"
        )


@router.put("/{remark_id}", response_model=dict)
async def update_remark(remark_id: int, remark_data: dict):
    """
    Update a remark
    """
    try:
        log_request({"remark_id": remark_id, "data": remark_data}, logger)
        
        supabase = get_supabase_client()
        
        # Update remark
        result = supabase.table("remarks").update(remark_data).eq("id", remark_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remark not found"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"remark_id": remark_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update remark"
        )


@router.delete("/{remark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_remark(remark_id: int):
    """
    Delete a remark
    """
    try:
        log_request({"remark_id": remark_id}, logger)
        
        supabase = get_supabase_client()
        
        # Delete remark
        result = supabase.table("remarks").delete().eq("id", remark_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remark not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"remark_id": remark_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete remark"
        )