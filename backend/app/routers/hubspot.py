import time
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas import (
    HubSpotContactSync,
    HubSpotSyncResponse,
    HubSpotContactCreate,
    HubSpotContactUpdate,
    HubSpotContactResponse,
)
from hubspot_utils import (
    normalize_phone,
    ensure_contact_properties,
    hubspot_request,
    find_contact_by_phone,
    find_contact_by_email,
    find_contact_by_name,
)
from app.logging_config import log_request, log_response, log_error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hubspot", tags=["HubSpot Integration"])


# ============================================================================
# Health & Properties
# ============================================================================

@router.get("/health", response_model=dict)
async def hubspot_health():
    """Check HubSpot integration health"""
    try:
        ensure_contact_properties()
        return {"status": "healthy", "message": "HubSpot connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"HubSpot connection failed: {str(e)}"
        )


@router.get("/properties", response_model=dict)
async def get_hubspot_properties():
    """Get list of custom HubSpot properties"""
    try:
        result = hubspot_request("/crm/v3/properties/contacts")
        return {"properties": result.get("results", [])}
    except Exception as e:
        log_error(e, logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch properties"
        )


# ============================================================================
# Sync Endpoints
# ============================================================================

@router.post("/sync/contact", response_model=HubSpotSyncResponse, status_code=status.HTTP_200_OK)
async def sync_contact_to_hubspot(contact_data: HubSpotContactSync):
    """
    Sync contact to HubSpot with duplicate prevention
    """
    start_time = time.time()
    
    try:
        log_request(contact_data.dict(), logger)
        
        normalized_phone = normalize_phone(contact_data.phone)
        ensure_contact_properties()
        
        first_name = contact_data.name.split()[0] if contact_data.name else "Patient"
        last_name = " ".join(contact_data.name.split()[1:]) if " " in contact_data.name else ""
        
        contact_id, contact_props = upsert_contact_by_phone(
            normalized_phone,
            first_name,
            last_name
        )
        
        new_properties = {
            "firstname": first_name,
            "lastname": last_name,
            "phone": normalized_phone,
        }
        
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
        
        merged_properties = merge_contact_data(contact_props, new_properties)
        
        hubspot_request(
            f"/crm/v3/objects/contacts/{contact_id}",
            method="PATCH",
            payload={"properties": merged_properties}
        )
        
        is_new = "id" not in contact_props or contact_props.get("id") != contact_id
        status_value = "created" if is_new else "merged"
        
        result = HubSpotSyncResponse(
            status=status_value,
            hubspot_id=contact_id,
            message=f"Contact {status_value} successfully",
            phone_normalized=normalized_phone
        )
        
        duration = time.time() - start_time
        log_response(result.dict(), logger, duration)
        
        return result
        
    except ValueError as e:
        log_error(e, logger, {"contact": contact_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        log_error(e, logger, {"contact": contact_data.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HubSpot sync failed: {str(e)}"
        )


@router.post("/sync/batch", response_model=dict, status_code=status.HTTP_200_OK)
async def batch_sync_contacts(contacts: list[HubSpotContactSync]):
    """
    Batch sync multiple contacts to HubSpot
    """
    start_time = time.time()
    
    try:
        log_request({"count": len(contacts)}, logger)
        
        ensure_contact_properties()
        
        results = []
        errors = []
        
        for idx, contact_data in enumerate(contacts):
            try:
                normalized_phone = normalize_phone(contact_data.phone)
                
                first_name = contact_data.name.split()[0] if contact_data.name else "Patient"
                last_name = " ".join(contact_data.name.split()[1:]) if " " in contact_data.name else ""
                
                contact_id, contact_props = upsert_contact_by_phone(
                    normalized_phone,
                    first_name,
                    last_name
                )
                
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
                
                merged_properties = merge_contact_data(contact_props, new_properties)
                
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
        
        log_response(response, logger, duration)
        
        return response
        
    except Exception as e:
        log_error(e, logger)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch sync failed"
        )


# ============================================================================
# HubSpot Contact CRUD Endpoints
# ============================================================================

@router.get("/contacts", response_model=List[HubSpotContactResponse])
async def get_hubspot_contacts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
):
    """
    Get all HubSpot contacts with pagination and optional search
    
    - **limit**: Number of contacts to return (1-100)
    - **offset**: Number of contacts to skip
    - **search**: Search by name, email, or phone (optional)
    """
    try:
        properties = [
            "firstname", "lastname", "phone", "email", "age", "gender",
            "condition", "dominant_hand", "patient_code", "device_id",
            "trial_1", "trial_2", "trial_3", "average_trial",
            "posture", "test_date", "created_at", "last_synced_reading_at"
        ]
        
        if search:
            search_payload = {
                "filterGroups": [{
                    "filters": [
                        {
                            "propertyName": "firstname",
                            "operator": "CONTAINS_TOKEN",
                            "value": search,
                        },
                        {
                            "propertyName": "lastname",
                            "operator": "CONTAINS_TOKEN",
                            "value": search,
                        },
                    ]
                }],
                "properties": properties,
                "limit": limit,
                "after": str(offset) if offset else None,
            }
            if search and "@" in search and "." in search:
                search_payload["filterGroups"][0]["filters"].append({
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": search,
                })
            
            # Remove None values
            search_payload = {k: v for k, v in search_payload.items() if v is not None}
            result = hubspot_request("/crm/v3/objects/contacts/search", method="POST", payload=search_payload)
        else:
            search_payload = {
                "properties": properties,
                "limit": limit,
                "after": str(offset) if offset else None,
            }
            search_payload = {k: v for k, v in search_payload.items() if v is not None}
            result = hubspot_request("/crm/v3/objects/contacts/search", method="POST", payload=search_payload)
        
        contacts = []
        for contact in result.get("results", []):
            props = contact.get("properties", {})
            contacts.append(HubSpotContactResponse(
                id=contact["id"],
                firstname=props.get("firstname"),
                lastname=props.get("lastname"),
                phone=props.get("phone"),
                email=props.get("email"),
                age=int(props["age"]) if props.get("age") else None,
                gender=props.get("gender"),
                condition=props.get("condition"),
                dominant_hand=props.get("dominant_hand"),
                patient_code=props.get("patient_code"),
                device_id=props.get("device_id"),
                trial_1=float(props["trial_1"]) if props.get("trial_1") else None,
                trial_2=float(props["trial_2"]) if props.get("trial_2") else None,
                trial_3=float(props["trial_3"]) if props.get("trial_3") else None,
                average_trial=float(props["average_trial"]) if props.get("average_trial") else None,
                posture=props.get("posture"),
                test_date=props.get("test_date"),
                last_synced_reading_at=props.get("last_synced_reading_at"),
            ))
        
        return contacts
    except Exception as e:
        log_error(e, logger, {"endpoint": "get_hubspot_contacts"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch HubSpot contacts"
        )


@router.get("/contacts/{contact_id}", response_model=HubSpotContactResponse)
async def get_hubspot_contact(contact_id: str):
    """
    Get HubSpot contact by ID
    
    - **contact_id**: HubSpot contact ID
    """
    try:
        properties = [
            "firstname", "lastname", "phone", "email", "age", "gender",
            "condition", "dominant_hand", "patient_code", "device_id",
            "trial_1", "trial_2", "trial_3", "average_trial",
            "posture", "test_date", "created_at", "last_synced_reading_at"
        ]
        
        result = hubspot_request(
            f"/crm/v3/objects/contacts/{contact_id}",
            params={"properties": ",".join(properties)}
        )
        
        props = result.get("properties", {})
        
        return HubSpotContactResponse(
            id=result["id"],
            firstname=props.get("firstname"),
            lastname=props.get("lastname"),
            phone=props.get("phone"),
            email=props.get("email"),
            age=int(props["age"]) if props.get("age") else None,
            gender=props.get("gender"),
            condition=props.get("condition"),
            dominant_hand=props.get("dominant_hand"),
            patient_code=props.get("patient_code"),
            device_id=props.get("device_id"),
            trial_1=float(props["trial_1"]) if props.get("trial_1") else None,
            trial_2=float(props["trial_2"]) if props.get("trial_2") else None,
            trial_3=float(props["trial_3"]) if props.get("trial_3") else None,
            average_trial=float(props["average_trial"]) if props.get("average_trial") else None,
            posture=props.get("posture"),
            test_date=props.get("test_date"),
            last_synced_reading_at=props.get("last_synced_reading_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"contact_id": contact_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch HubSpot contact"
        )


@router.post("/contacts", response_model=HubSpotContactResponse, status_code=status.HTTP_201_CREATED)
async def create_hubspot_contact(contact: HubSpotContactCreate):
    """
    Create new HubSpot contact
    
    - **contact**: Contact data
    """
    try:
        log_request(contact.dict(), logger)
        
        ensure_contact_properties()
        
        normalized_phone = normalize_phone(contact.phone)
        
        # Check if contact already exists
        existing_id, existing_props = find_contact_by_phone(normalized_phone)
        if not existing_id and contact.email:
            existing_id, existing_props = find_contact_by_email(contact.email)
        if not existing_id and contact.firstname:
            existing_id, existing_props = find_contact_by_name(contact.firstname, contact.lastname or "")
            
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"HubSpot contact with phone {normalized_phone} or email {contact.email} already exists"
            )
        
        first_name = contact.firstname
        last_name = contact.lastname or ""
        
        # Build create payload
        create_payload = {
            "properties": {
                "firstname": first_name,
                "lastname": last_name,
                "phone": normalized_phone,
            }
        }
        
        if contact.email:
            create_payload["properties"]["email"] = contact.email
        if contact.age is not None:
            create_payload["properties"]["age"] = str(contact.age)
        if contact.gender:
            create_payload["properties"]["gender"] = contact.gender
        if contact.condition:
            create_payload["properties"]["condition"] = contact.condition
        if contact.dominant_hand:
            create_payload["properties"]["dominant_hand"] = contact.dominant_hand
        if contact.patient_code:
            create_payload["properties"]["patient_code"] = contact.patient_code
        if contact.device_id:
            create_payload["properties"]["device_id"] = contact.device_id
        if contact.trial_1 is not None:
            create_payload["properties"]["trial_1"] = str(contact.trial_1)
        if contact.trial_2 is not None:
            create_payload["properties"]["trial_2"] = str(contact.trial_2)
        if contact.trial_3 is not None:
            create_payload["properties"]["trial_3"] = str(contact.trial_3)
        if contact.average_trial is not None:
            create_payload["properties"]["average_trial"] = str(contact.average_trial)
        if contact.posture:
            create_payload["properties"]["posture"] = contact.posture
        if contact.test_date:
            create_payload["properties"]["test_date"] = contact.test_date.isoformat()
        
        # Create contact
        result = hubspot_request("/crm/v3/objects/contacts", method="POST", payload=create_payload)
        props = result.get("properties", {})
        
        created_contact = HubSpotContactResponse(
            id=result["id"],
            firstname=props.get("firstname"),
            lastname=props.get("lastname"),
            phone=props.get("phone"),
            email=props.get("email"),
            age=int(props["age"]) if props.get("age") else None,
            gender=props.get("gender"),
            condition=props.get("condition"),
            dominant_hand=props.get("dominant_hand"),
            patient_code=props.get("patient_code"),
            device_id=props.get("device_id"),
            trial_1=float(props["trial_1"]) if props.get("trial_1") else None,
            trial_2=float(props["trial_2"]) if props.get("trial_2") else None,
            trial_3=float(props["trial_3"]) if props.get("trial_3") else None,
            average_trial=float(props["average_trial"]) if props.get("average_trial") else None,
            posture=props.get("posture"),
            test_date=props.get("test_date"),
            last_synced_reading_at=props.get("last_synced_reading_at"),
        )
        
        log_response(created_contact.dict(), logger)
        return created_contact
        
    except HTTPException:
        raise
    except ValueError as e:
        log_error(e, logger, {"contact": contact.dict()})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        log_error(e, logger, {"contact": contact.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create HubSpot contact"
        )


@router.patch("/contacts/{contact_id}", response_model=HubSpotContactResponse)
async def update_hubspot_contact(contact_id: str, contact: HubSpotContactUpdate):
    """
    Update HubSpot contact
    
    - **contact_id**: HubSpot contact ID
    - **contact**: Updated contact data
    """
    try:
        log_request({"contact_id": contact_id, "data": contact.dict()}, logger)
        
        ensure_contact_properties()
        
        # Fetch existing contact first
        existing_result = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}")
        existing_props = existing_result.get("properties", {})
        
        # Build update payload
        new_properties = {}
        
        if contact.firstname is not None:
            new_properties["firstname"] = contact.firstname
        elif existing_props.get("firstname"):
            new_properties["firstname"] = existing_props["firstname"]
            
        if contact.lastname is not None:
            new_properties["lastname"] = contact.lastname
        elif existing_props.get("lastname"):
            new_properties["lastname"] = existing_props["lastname"]
            
        if contact.phone is not None:
            new_properties["phone"] = normalize_phone(contact.phone)
        elif existing_props.get("phone"):
            new_properties["phone"] = existing_props["phone"]
            
        if contact.email is not None:
            new_properties["email"] = contact.email
        elif existing_props.get("email"):
            new_properties["email"] = existing_props["email"]
        
        if contact.age is not None:
            new_properties["age"] = str(contact.age)
        elif existing_props.get("age"):
            new_properties["age"] = existing_props["age"]
            
        if contact.gender is not None:
            new_properties["gender"] = contact.gender
        elif existing_props.get("gender"):
            new_properties["gender"] = existing_props["gender"]
            
        if contact.condition is not None:
            new_properties["condition"] = contact.condition
        elif existing_props.get("condition"):
            new_properties["condition"] = existing_props["condition"]
            
        if contact.dominant_hand is not None:
            new_properties["dominant_hand"] = contact.dominant_hand
        elif existing_props.get("dominant_hand"):
            new_properties["dominant_hand"] = existing_props["dominant_hand"]
            
        if contact.patient_code is not None:
            new_properties["patient_code"] = contact.patient_code
        elif existing_props.get("patient_code"):
            new_properties["patient_code"] = existing_props["patient_code"]
            
        if contact.device_id is not None:
            new_properties["device_id"] = contact.device_id
        elif existing_props.get("device_id"):
            new_properties["device_id"] = existing_props["device_id"]
            
        if contact.trial_1 is not None:
            new_properties["trial_1"] = str(contact.trial_1)
        elif existing_props.get("trial_1"):
            new_properties["trial_1"] = existing_props["trial_1"]
            
        if contact.trial_2 is not None:
            new_properties["trial_2"] = str(contact.trial_2)
        elif existing_props.get("trial_2"):
            new_properties["trial_2"] = existing_props["trial_2"]
            
        if contact.trial_3 is not None:
            new_properties["trial_3"] = str(contact.trial_3)
        elif existing_props.get("trial_3"):
            new_properties["trial_3"] = existing_props["trial_3"]
            
        if contact.average_trial is not None:
            new_properties["average_trial"] = str(contact.average_trial)
        elif existing_props.get("average_trial"):
            new_properties["average_trial"] = existing_props["average_trial"]
            
        if contact.posture is not None:
            new_properties["posture"] = contact.posture
        elif existing_props.get("posture"):
            new_properties["posture"] = existing_props["posture"]
            
        if contact.test_date is not None:
            new_properties["test_date"] = contact.test_date.isoformat()
        elif existing_props.get("test_date"):
            new_properties["test_date"] = existing_props["test_date"]
        
        hubspot_request(
            f"/crm/v3/objects/contacts/{contact_id}",
            method="PATCH",
            payload={"properties": new_properties}
        )
        
        # Fetch updated contact
        result = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}")
        props = result.get("properties", {})
        
        updated_contact = HubSpotContactResponse(
            id=result["id"],
            firstname=props.get("firstname"),
            lastname=props.get("lastname"),
            phone=props.get("phone"),
            email=props.get("email"),
            age=int(props["age"]) if props.get("age") else None,
            gender=props.get("gender"),
            condition=props.get("condition"),
            dominant_hand=props.get("dominant_hand"),
            patient_code=props.get("patient_code"),
            device_id=props.get("device_id"),
            trial_1=float(props["trial_1"]) if props.get("trial_1") else None,
            trial_2=float(props["trial_2"]) if props.get("trial_2") else None,
            trial_3=float(props["trial_3"]) if props.get("trial_3") else None,
            average_trial=float(props["average_trial"]) if props.get("average_trial") else None,
            posture=props.get("posture"),
            test_date=props.get("test_date"),
            last_synced_reading_at=props.get("last_synced_reading_at"),
        )
        
        log_response(updated_contact.dict(), logger)
        return updated_contact
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"contact_id": contact_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update HubSpot contact"
        )


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hubspot_contact(contact_id: str):
    """
    Delete HubSpot contact
    
    - **contact_id**: HubSpot contact ID
    """
    try:
        hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="DELETE")
        return None
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, logger, {"contact_id": contact_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete HubSpot contact"
        )