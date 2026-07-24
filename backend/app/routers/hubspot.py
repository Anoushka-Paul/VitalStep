"""
HubSpot Integration Router
Handles contact syncing with duplicate prevention
"""
import time
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.schemas import HubSpotContactSync, HubSpotSyncResponse
from app.hubspot_utils import (
    normalize_phone,
    upsert_contact_by_phone,
    merge_contact_data,
    ensure_contact_properties,
)
from app.logging_config import log_request, log_response, log_error

router = APIRouter(prefix="/hubspot", tags=["HubSpot Integration"])


@router.get("/health", response_model=dict)
async def hubspot_health():
    """Check HubSpot integration health"""
    try:
        # Try to ensure properties (lightweight operation)
        ensure_contact_properties()
        return {"status": "healthy", "message": "HubSpot connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"HubSpot connection failed: {str(e)}"
        )


@router.post("/sync/contact", response_model=HubSpotSyncResponse, status_code=status.HTTP_200_OK)
async def sync_contact_to_hubspot(contact_data: HubSpotContactSync):
    """
    Sync contact to HubSpot with duplicate prevention
    
    - **name**: Patient full name
    - **phone**: Phone number (any format, will be normalized)
    - **email**: Email address (optional)
    - **age**: Patient age (optional)
    - **dominant_hand**: Dominant hand (optional)
    - **patient_code**: Patient code (optional)
    - **trial1/trial2/trial3**: Trial readings (optional)
    - **average_trial**: Average of trials (optional)
    - **posture**: Posture during test (optional)
    - **test_date**: Date of test (optional)
    
    Returns sync status with HubSpot contact ID
    """
    start_time = time.time()
    
    try:
        log_request(contact_data.dict(), router.logger)
        
        # Normalize phone number
        normalized_phone = normalize_phone(contact_data.phone)
        
        # Ensure HubSpot properties exist
        ensure_contact_properties()
        
        # Prepare contact data
        first_name = contact_data.name.split()[0] if contact_data.name else "Patient"
        last_name = " ".join(contact_data.name.split()[1:]) if " " in contact_data.name else ""
        
        # Upsert contact (find or create)
        contact_id, contact_props = upsert_contact_by_phone(
            normalized_phone,
            first_name,
            last_name
        )
        
        # Build properties to update
        new_properties = {
            "firstname": first_name,
            "lastname": last_name,
            "phone": normalized_phone,
        }
        
        # Add optional fields
        if contact_data.email:
            new_properties["email"] = contact_data.email
        if contact_data.age:
            new_properties["age"] = str(contact_data.age)
        if contact_data.dominant_hand:
            new_properties["dominant_hand"] = contact_data.dominant_hand
        if contact_data.patient_code:
            new_properties["patient_code"] = contact_data.patient_code
        if contact_data.trial1 is not None:
            new_properties["trial_1"] = str(contact_data.trial1)
        if contact_data.trial2 is not None:
            new_properties["trial_2"] = str(contact_data.trial2)
        if contact_data.trial3 is not None:
            new_properties["trial_3"] = str(contact_data.trial3)
        if contact_data.average_trial is not None:
            new_properties["average_trial"] = str(contact_data.average_trial)
        if contact_data.posture:
            new_properties["posture"] = contact_data.posture
        if contact_data.test_date:
            new_properties["test_date"] = contact_data.test_date.isoformat()
        
        # Merge with existing data
        merged_properties = merge_contact_data(contact_props, new_properties)
        
        # Update contact in HubSpot
        from app.hubspot_utils import hubspot_request
        hubspot_request(
            f"/crm/v3/objects/contacts/{contact_id}",
            method="PATCH",
            payload={"properties": merged_properties}
        )
        
        # Determine status
        is_new = "id" not in contact_props or contact_props.get("id") != contact_id
        status_value = "created" if is_new else "merged"
        
        result = HubSpotSyncResponse(
            status=status_value,
            hubspot_id=contact_id,
            message=f"Contact {status_value} successfully",
            phone_normalized=normalized_phone
        )
        
        duration = time.time() - start_time
        log_response(result.dict(), router.logger, duration)
        
        return result
        
    except ValueError as e:
        log_error(e, router.logger, {"contact": contact_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        log_error(e, router.logger, {"contact": contact_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HubSpot sync failed: {str(e)}"
        )


@router.post("/sync/batch", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def batch_sync_contacts(contacts: list[HubSpotContactSync]):
    """
    Batch sync multiple contacts to HubSpot
    
    - **contacts**: List of contact data (max 50)
    
    Returns batch sync results
    """
    start_time = time.time()
    
    try:
        log_request({"count": len(contacts)}, router.logger)
        
        ensure_contact_properties()
        
        results = []
        errors = []
        
        for idx, contact_data in enumerate(contacts):
            try:
                # Normalize phone
                normalized_phone = normalize_phone(contact_data.phone)
                
                # Prepare contact info
                first_name = contact_data.name.split()[0] if contact_data.name else "Patient"
                last_name = " ".join(contact_data.name.split()[1:]) if " " in contact_data.name else ""
                
                # Upsert contact
                contact_id, contact_props = upsert_contact_by_phone(
                    normalized_phone,
                    first_name,
                    last_name
                )
                
                # Build properties
                new_properties = {
                    "firstname": first_name,
                    "lastname": last_name,
                    "phone": normalized_phone,
                }
                
                if contact_data.email:
                    new_properties["email"] = contact_data.email
                if contact_data.age:
                    new_properties["age"] = str(contact_data.age)
                if contact_data.average_trial is not None:
                    new_properties["average_trial"] = str(contact_data.average_trial)
                
                # Merge and update
                merged_properties = merge_contact_data(contact_props, new_properties)
                
                from app.hubspot_utils import hubspot_request
                hubspot_request(
                    f"/crm/v3/objects/contacts/{contact_id}",
                    method="PATCH",
                    payload={"properties": merged_properties}
                )
                
                results.append({
                    "index": idx,
                    "status": "success",
                    "hubspot_id": contact_id,
                    "phone": normalized_phone
                })
                
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": str(e),
                    "contact": contact_data.dict()
                })
        
        duration = time.time() - start_time
        
        response = {
            "total": len(contacts),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "duration_seconds": round(duration, 2)
        }
        
        log_response(response, router.logger, duration)
        
        return response
        
    except Exception as e:
        log_error(e, router.logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch sync failed"
        )


@router.get("/properties", response_model=dict)
async def get_hubspot_properties():
    """Get list of custom HubSpot properties"""
    try:
        from app.hubspot_utils import hubspot_request
        result = hubspot_request("/crm/v3/properties/contacts")
        return {"properties": result.get("results", [])}
    except Exception as e:
        log_error(e, router.logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch properties"
        )