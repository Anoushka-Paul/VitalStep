"""
Patients Router
Handles patient CRUD operations and trial readings
"""
import os
import sys
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas import (
    PatientCreate,
    PatientResponse,
    TrialReadingCreate,
    TrialReadingResponse,
    TrialReadingWithPatient,
)
from app.database import PatientRepository, TrialReadingRepository
from app.logging_config import log_request, log_response, log_error

# Add backend directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hubspot_utils import (
    normalize_phone,
    ensure_contact_properties,
    upsert_contact_by_phone,
    is_email as hubspot_is_email,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


# ============================================================================
# Patient Endpoints
# ============================================================================

@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    database: str = "primary"
):
    """
    Get all patients with pagination
    
    - **limit**: Number of patients to return (1-100)
    - **offset**: Number of patients to skip
    - **search**: Search by name (optional)
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        repo = PatientRepository(database=database)
        
        if search:
            patients = repo.search_by_name(search, limit=limit)
        else:
            patients = repo.get_all(limit=limit, offset=offset)
        
        return patients
    except Exception as e:
        log_error(e, router.logger, {"endpoint": "get_patients"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch patients"
        )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, database: str = "primary"):
    """
    Get patient by ID
    
    - **patient_id**: Patient ID
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        repo = PatientRepository(database=database)
        patient = repo.get_by_id(patient_id)
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        return patient
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch patient"
        )


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate, database: str = "primary"):
    """
    Create new patient
    
    - **patient**: Patient data
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        log_request(patient.dict(), router.logger)
        
        repo = PatientRepository(database=database)
        
        # Check if patient already exists by phone
        existing = repo.get_by_phone(patient.contact)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with phone {patient.contact} already exists"
            )
        
        # Create patient
        patient_data = patient.dict()
        created_patient = repo.create(patient_data)
        
        log_response(created_patient, router.logger)
        
        # Auto-sync to HubSpot (non-blocking)
        try:
            contact = created_patient.get("contact", "")
            if contact:
                email = ""
                phone = ""
                if hubspot_is_email(contact):
                    email = contact
                else:
                    phone = normalize_phone(contact)
                
                if phone or email:
                    first_name = created_patient.get("name", "").split()[0] if created_patient.get("name") else "Patient"
                    last_name = " ".join(created_patient.get("name", "").split()[1:]) if created_patient.get("name") and " " in created_patient.get("name") else ""
                    
                    # Ensure HubSpot properties exist
                    ensure_contact_properties()
                    
                    # Create/update contact in HubSpot
                    contact_id, _ = upsert_contact_by_phone(phone, first_name, last_name, email)
                    
                    # Update with additional fields
                    update_payload = {
                        "properties": {
                            "firstname": first_name,
                            "lastname": last_name,
                            "phone": phone,
                            "email": email,
                            "device_id": created_patient.get("host_user_id"),
                        }
                    }
                    
                    # Add optional fields
                    if created_patient.get("age"):
                        update_payload["properties"]["age"] = str(created_patient.get("age"))
                    if created_patient.get("gender"):
                        update_payload["properties"]["gender"] = created_patient.get("gender")
                    if created_patient.get("patient_code"):
                        update_payload["properties"]["patient_code"] = created_patient.get("patient_code")
                    if created_patient.get("dominant_hand"):
                        update_payload["properties"]["dominant_hand"] = created_patient.get("dominant_hand")
                    if created_patient.get("condition"):
                        update_payload["properties"]["condition"] = created_patient.get("condition")
                    if created_patient.get("dob"):
                        update_payload["properties"]["test_date"] = created_patient.get("dob")
                    
                    # Make HubSpot API call
                    import requests
                    from dotenv import load_dotenv
                    load_dotenv()
                    hubspot_pat = os.getenv("HUBSPOT_PAT")
                    
                    if hubspot_pat:
                        headers = {
                            "Authorization": f"Bearer {hubspot_pat}",
                            "Content-Type": "application/json",
                        }
                        url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
                        requests.patch(url, headers=headers, json=update_payload, timeout=10)
        except Exception as exc:
            # Log but don't fail patient creation if HubSpot sync fails
            log_error(exc, router.logger, {"patient_id": created_patient.get("id"), "hubspot_sync": True})
        
        return created_patient
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient": patient.dict()})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create patient"
        )


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: int, patient: PatientCreate, database: str = "primary"):
    """
    Update patient
    
    - **patient_id**: Patient ID to update
    - **patient**: Updated patient data
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        log_request({"patient_id": patient_id, "data": patient.dict()}, router.logger)
        
        repo = PatientRepository(database=database)
        
        # Check if patient exists
        existing = repo.get_by_id(patient_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # Update patient
        updated_patient = repo.update(patient_id, patient.dict())
        
        log_response(updated_patient, router.logger)
        
        return updated_patient
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient"
        )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int, database: str = "primary"):
    """
    Delete patient
    
    - **patient_id**: Patient ID to delete
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        repo = PatientRepository(database=database)
        
        # Check if patient exists
        existing = repo.get_by_id(patient_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # Delete patient
        repo.delete(patient_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient"
        )


# ============================================================================
# Trial Reading Endpoints
# ============================================================================

@router.get("/{patient_id}/readings", response_model=List[TrialReadingResponse])
async def get_patient_readings(
    patient_id: int,
    limit: int = Query(10, ge=1, le=100),
    database: str = "primary"
):
    """
    Get all trial readings for a patient
    
    - **patient_id**: Patient ID
    - **limit**: Number of readings to return
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        repo = TrialReadingRepository(database=database)
        readings = repo.get_by_patient(patient_id, limit=limit)
        return readings
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch readings"
        )


@router.get("/{patient_id}/readings/latest", response_model=TrialReadingWithPatient)
async def get_latest_reading(patient_id: int, database: str = "primary"):
    """
    Get latest trial reading for a patient
    
    - **patient_id**: Patient ID
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        repo = TrialReadingRepository(database=database)
        reading = repo.get_latest_by_patient(patient_id)
        
        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No readings found for patient {patient_id}"
            )
        
        # Add patient details
        patient_repo = PatientRepository(database=database)
        patient = patient_repo.get_by_id(patient_id)
        
        if patient:
            reading["patient_name"] = patient.get("name")
            reading["patient_contact"] = patient.get("contact")
        
        return reading
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch latest reading"
        )


@router.post("/{patient_id}/readings", response_model=TrialReadingResponse, status_code=status.HTTP_201_CREATED)
async def create_trial_reading(patient_id: int, reading: TrialReadingCreate, database: str = "primary"):
    """
    Create new trial reading for patient
    
    - **patient_id**: Patient ID
    - **reading**: Trial reading data
    - **database**: Database to use ("primary" or "secondary")
    """
    try:
        log_request({"patient_id": patient_id, "reading": reading.dict()}, router.logger)
        
        # Verify patient exists
        patient_repo = PatientRepository(database=database)
        patient = patient_repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # Create reading
        reading_data = reading.dict()
        reading_data["patient_id"] = patient_id
        
        # Calculate average
        reading_data["average"] = round(
            (reading.trial1 + reading.trial2 + reading.trial3) / 3, 2
        )
        
        repo = TrialReadingRepository(database=database)
        created_reading = repo.create(reading_data)
        
        log_response(created_reading, router.logger)
        
        return created_reading
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, router.logger, {"patient_id": patient_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reading"
        )