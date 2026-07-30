"""
Devices Router
Handles device operations
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/device", tags=["Devices"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class DeviceResponse(BaseModel):
    id: str
    device_code: str
    user_id: Optional[str]
    status: str
    created_at: str


# ============================================================================
# Device Endpoints
# ============================================================================

@router.get("/queue", response_model=List[dict])
async def get_device_queue():
    """
    Get all available devices in queue
    """
    try:
        log_request({}, logger)
        
        supabase = get_supabase_client()
        
        # Get all devices
        result = supabase.table("devices").select("*").execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch devices"
        )


@router.get("/{device_id}", response_model=dict)
async def get_device(device_id: str):
    """
    Get device by ID
    """
    try:
        log_request({"device_id": device_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get device
        result = supabase.table("devices").select("*").eq("id", device_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"device_id": device_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch device"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_device(device_data: dict):
    """
    Register a new device
    """
    try:
        log_request(device_data, logger)
        
        supabase = get_supabase_client()
        
        # Insert device
        result = supabase.table("devices").insert(device_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create device"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"device_data": device_data})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create device"
        )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    """
    Delete a device
    """
    try:
        log_request({"device_id": device_id}, logger)
        
        supabase = get_supabase_client()
        
        # Delete device
        result = supabase.table("devices").delete().eq("id", device_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"device_id": device_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device"
        )