"""
Account Access Router
Handles specialist-patient account access relationships
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

from app.config import settings
from app.logging_config import log_request, log_response, log_error
from supabase import create_client

router = APIRouter(prefix="/accountAccess", tags=["Account Access"])


def get_supabase_client():
    """Get Supabase client"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


# ============================================================================
# Request/Response Models
# ============================================================================

class AccountAccessCreateRequest(BaseModel):
    specialist_id: str
    patient_id: str
    access_type: str = "read"  # "read", "write", "admin"


class AccountAccessResponse(BaseModel):
    id: int
    specialist_id: str
    patient_id: str
    access_type: str
    created_at: str


# ============================================================================
# Account Access Endpoints
# ============================================================================

@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_account_access(user_id: str):
    """
    Get all account access records for a user (as specialist)
    """
    try:
        log_request({"user_id": user_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get account access records where user is specialist
        result = supabase.table("account_access").select("*").eq("specialist_id", user_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch account access"
        )


@router.get("/patient/{patient_id}", response_model=List[dict])
async def get_patient_specialists(patient_id: str):
    """
    Get all specialists with access to a patient
    """
    try:
        log_request({"patient_id": patient_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get account access records where user is patient
        result = supabase.table("account_access").select("*").eq("patient_id", patient_id).execute()
        
        log_response({"count": len(result.data)}, logger)
        
        return result.data
        
    except Exception as e:
        log_error(e, logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch patient specialists"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_account_access(access_data: AccountAccessCreateRequest):
    """
    Grant specialist access to patient
    """
    try:
        log_request(access_data.dict(), logger)
        
        supabase = get_supabase_client()
        
        # Prepare access data
        access_dict = {
            "specialist_id": access_data.specialist_id,
            "patient_id": access_data.patient_id,
            "access_type": access_data.access_type,
            "created_at": "now()"
        }
        
        # Insert account access
        result = supabase.table("account_access").insert(access_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account access"
            )
        
        log_response(result.data[0], logger)
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"access_data": access_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account access"
        )


@router.delete("/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account_access(access_id: int):
    """
    Revoke specialist access to patient
    """
    try:
        log_request({"access_id": access_id}, logger)
        
        supabase = get_supabase_client()
        
        # Delete account access
        result = supabase.table("account_access").delete().eq("id", access_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account access not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"access_id": access_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account access"
        )


@router.get("/specialist/{specialist_id}/patients", response_model=List[dict])
async def get_specialist_patients(specialist_id: str):
    """
    Get all patients accessible to a specialist
    """
    try:
        log_request({"specialist_id": specialist_id}, logger)
        
        supabase = get_supabase_client()
        
        # Get all account access records for specialist
        access_result = supabase.table("account_access").select("*").eq("specialist_id", specialist_id).execute()
        
        if not access_result.data:
            return []
        
        # Get patient IDs
        patient_ids = [access["patient_id"] for access in access_result.data]
        
        # Get patient details
        patients = []
        for patient_id in patient_ids:
            patient_result = supabase.table("profiles").select("*").eq("id", patient_id).execute()
            if patient_result.data:
                patients.append(patient_result.data[0])
        
        log_response({"count": len(patients)}, logger)
        
        return patients
        
    except Exception as e:
        log_error(e, logger, {"specialist_id": specialist_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch specialist patients"
        )