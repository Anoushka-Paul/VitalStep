import os
import json
from fastapi import FastAPI, BackgroundTasks
from dotenv import load_dotenv

# Load local .env when present
load_dotenv()

# Import shared HubSpot utilities
from hubspot_utils import (
    supabase_request,
    hubspot_request,
    normalize_phone,
    ensure_contact_properties,
    find_contact_by_phone,
    upsert_contact_by_phone,
    merge_contact_data,
)

app = FastAPI(title="VitalStep Sync API")


def ensure_contact_properties() -> None:
    for name, label, prop_type, field_type in [
        ("dominant_hand", "Dominant Hand", "string", "text"),
        ("patient_code", "Patient Code", "string", "text"),
        ("age", "Age", "number", "number"),
        ("test_date", "Test Date", "datetime", "date"),
        ("posture", "Posture", "string", "text"),
        ("trial_1", "Trial 1", "number", "number"),
        ("trial_2", "Trial 2", "number", "number"),
        ("trial_3", "Trial 3", "number", "number"),
        ("average_trial", "Average Trial", "number", "number"),
        ("created_at", "Created At", "datetime", "date"),
    ]:
        payload = {
            "name": name,
            "label": label,
            "type": prop_type,
            "fieldType": field_type,
            "groupName": "contactinformation",
        }
        try:
            hubspot_request("/crm/v3/properties/contacts", method="POST", payload=payload)
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" not in message and "duplicate" not in message and "400" not in message:
                raise


def build_contact_properties(data: dict) -> dict:
    properties = {}
    if data.get("name"):
        properties["firstname"] = str(data["name"]).strip()

    if data.get("phone"):
        # Normalize phone number before storing
        properties["phone"] = normalize_phone(str(data["phone"]).strip())

    for source_key, target_key in [
        ("dominantHand", "dominant_hand"),
        ("patientCode", "patient_code"),
        ("age", "age"),
        ("testDate", "test_date"),
        ("posture", "posture"),
        ("trial1", "trial_1"),
        ("trial2", "trial_2"),
        ("trial3", "trial_3"),
        ("averageTrial", "average_trial"),
        ("createdAt", "created_at"),
    ]:
        value = data.get(source_key)
        if value is None or value == "":
            properties[target_key] = None
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            properties[target_key] = str(value)
        else:
            properties[target_key] = str(value)

    return properties


def sync_app_contact_to_hubspot(data: dict) -> dict:
    """
    Sync contact from app to HubSpot.
    Uses normalized phone numbers and MERGES data instead of skipping.
    """
    phone = str(data.get("phone") or "").strip()
    if not phone:
        return {"status": "skipped", "reason": "missing_phone"}

    # Normalize phone number
    normalized_phone = normalize_phone(phone)
    
    first_name = str(data.get("name") or "Patient").strip() or "Patient"
    last_name = ""

    # Use the improved upsert function that handles phone normalization
    contact_id, contact_props = upsert_contact_by_phone(normalized_phone, first_name, last_name)

    ensure_contact_properties()

    properties = build_contact_properties(data)
    if not properties:
        return {"status": "skipped", "reason": "no_properties"}

    # MERGE with existing data instead of overwriting
    merged_properties = merge_contact_data(contact_props, properties)
    
    # Always update the contact with merged data
    payload = {"properties": merged_properties}
    hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
    
    return {"status": "merged", "hubspot_id": contact_id}


def run_supabase_to_hubspot_sync(limit: int = 20) -> dict:
    """
    Sync patients from Supabase to HubSpot.
    Uses normalized phone numbers and always updates existing contacts.
    """
    # Ensure properties exist
    ensure_contact_properties()

    patients = supabase_request("/rest/v1/research_patients", params={"select": "id,name,contact", "order": "created_at.desc", "limit": str(limit)})
    synced = []
    for patient in patients:
        patient_id = patient.get("id")
        name = patient.get("name") or ""
        contact = (patient.get("contact") or "").strip()
        if not patient_id:
            continue

        readings = supabase_request(
            "/rest/v1/patient_readings",
            params={"select": "trial1,trial2,trial3,hand,posture,assessment_type,created_at", "patient_id": f"eq.{patient_id}", "order": "created_at.desc", "limit": "1"},
        )
        if not readings:
            continue

        latest = readings[0]
        try:
            trial1 = float(latest.get("trial1", 0))
            trial2 = float(latest.get("trial2", 0))
            trial3 = float(latest.get("trial3", 0))
        except Exception:
            continue
        average = round((trial1 + trial2 + trial3) / 3, 2)

        # Normalize phone number
        phone = normalize_phone(contact) if contact else ""

        if not phone:
            continue

        first_name = name.split()[0] if name else "Patient"
        last_name = " ".join(name.split()[1:]) if " " in name else ""
        
        # Use improved upsert that handles phone normalization
        contact_id, contact_props = upsert_contact_by_phone(phone, first_name, last_name)

        # Idempotency: skip if this reading is already synced
        last_synced = contact_props.get("last_synced_reading_at")
        latest_created_at = latest.get("created_at")
        if last_synced and latest_created_at and str(last_synced) == str(latest_created_at):
            continue

        # Build payload with all data
        payload = {
            "properties": {
                "firstname": first_name,
                "lastname": last_name,
                "phone": phone,
                "trial_1": str(trial1),
                "trial_2": str(trial2),
                "trial_3": str(trial3),
                "average_trial": str(average),
                "average_kg": str(average),
                "trial_source": "supabase_patient_reading",
                "trial_payload_json": json.dumps({
                    "patient_name": name,
                    "trial_readings": {"trial_1": trial1, "trial_2": trial2, "trial_3": trial3},
                    "average_trial": average,
                    "hand": latest.get("hand"),
                    "posture": latest.get("posture"),
                    "assessment_type": latest.get("assessment_type"),
                    "created_at": latest_created_at,
                }),
                "last_synced_reading_at": latest_created_at,
            }
        }
        try:
            res = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
            synced.append({"patient": name, "phone": phone, "hubspot_id": contact_id, "avg": average})
        except Exception:
            continue

    return {"synced_count": len(synced), "synced": synced}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sync/supabase")
def sync_supabase(background_tasks: BackgroundTasks, limit: int = 20):
    # kick off background sync and return immediately
    background_tasks.add_task(run_supabase_to_hubspot_sync, limit)
    return {"status": "started", "limit": limit}


@app.post("/sync/supabase/block")
def sync_supabase_block(limit: int = 20):
    # run synchronously and return result
    result = run_supabase_to_hubspot_sync(limit)
    return result


@app.post("/sync/app-contact")
def sync_app_contact(payload: dict):
    return sync_app_contact_to_hubspot(payload)
