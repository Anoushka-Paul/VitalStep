"""
Sync Supabase trial data to HubSpot contacts.
Uses normalized phone numbers to prevent duplicates and merge data properly.
"""
import json
import os
import sys

# Add parent directory to path to import hubspot_utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from hubspot_utils import (
    supabase_request,
    hubspot_request,
    normalize_phone,
    ensure_contact_properties,
    upsert_contact_by_phone,
    merge_contact_data,
)

SUPABASE_URL = "https://cbebmpgsbxqdzpfgqulj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiZWJtcGdzYnhxZHpwZmdxdWxqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwNjQ3MjEsImV4cCI6MjA5ODY0MDcyMX0.n5oOlnR1GFWDG2SxLOlmW1B_NPvnhABl7Kv-pP5mtKY"
HUBSPOT_PAT = os.getenv("HUBSPOT_PAT")


def read_google_sheet_rows(sheet_id: str, range_name: str):
    """Placeholder: read rows from a Google Sheet.

    Implement using Google Sheets API and a service account or OAuth credentials.
    Returns list of row dicts. Left as a placeholder because auth requires
    credentials and user consent; we'll wire this when you provide access.
    """
    raise NotImplementedError("Google Sheets integration not implemented yet")


def ensure_property(name: str, label: str, prop_type: str, field_type: str):
    payload = {
        "name": name,
        "label": label,
        "type": prop_type,
        "fieldType": field_type,
        "groupName": "contactinformation",
    }
    try:
        hubspot_request("/crm/v3/properties/contacts", method="POST", payload=payload)
        print(f"Created property: {name}")
    except RuntimeError as exc:
        if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
            print(f"Property already exists: {name}")
        else:
            raise


if __name__ == "__main__":
    ensure_property("trial_1", "Trial 1", "number", "number")
    ensure_property("trial_2", "Trial 2", "number", "number")
    ensure_property("trial_3", "Trial 3", "number", "number")
    ensure_property("average_trial", "Average Trial", "number", "number")
    ensure_property("trial_source", "Trial Source", "string", "text")
    ensure_property("trial_payload_json", "Trial Payload JSON", "string", "text")
    ensure_property("last_synced_reading_at", "Last Synced Reading At", "string", "text")

    patients = supabase_request("/rest/v1/research_patients", params={"select": "id,name,contact", "order": "created_at.desc", "limit": "20"})
    if not patients:
        print("No patients found in Supabase.")
        sys.exit(0)

    print(f"Found {len(patients)} patient(s) in Supabase.")
    for patient in patients:
        patient_id = patient.get("id")
        name = patient.get("name") or ""
        contact = (patient.get("contact") or "").strip()
        if not patient_id:
            continue

        readings = supabase_request(
            "/rest/v1/patient_readings",
            params={
                "select": "trial1,trial2,trial3,hand,posture,assessment_type,created_at",
                "patient_id": f"eq.{patient_id}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if not readings:
            print(f"No readings found for {name}")
            continue

        latest = readings[0]
        trial1 = float(latest.get("trial1", 0))
        trial2 = float(latest.get("trial2", 0))
        trial3 = float(latest.get("trial3", 0))
        average = round((trial1 + trial2 + trial3) / 3, 2)

        # Normalize phone number
        phone = normalize_phone(contact) if contact else ""

        if not phone:
            print(f"Skipping {name}: no phone number available")
            continue

        first_name = name.split()[0] if name else "Patient"
        last_name = " ".join(name.split()[1:]) if " " in name else ""
        
        # Use improved upsert that handles phone normalization
        contact_id, contact_props = upsert_contact_by_phone(phone, first_name, last_name)

        # Idempotency: skip if this reading is already the last synced one
        last_synced = contact_props.get("last_synced_reading_at")
        latest_created_at = latest.get("created_at")
        if last_synced and latest_created_at and str(last_synced) == str(latest_created_at):
            print(f"Skipping {name} ({phone}): latest reading already synced at {last_synced}")
            continue

        # Build new data payload
        new_data = {
            "firstname": first_name,
            "lastname": last_name,
            "phone": phone,
            "trial_1": str(trial1),
            "trial_2": str(trial2),
            "trial_3": str(trial3),
            "average_trial": str(average),
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
            # mark the timestamp we synced so next run can skip duplicates
            "last_synced_reading_at": latest_created_at,
        }
        
        # MERGE with existing data instead of overwriting
        merged_properties = merge_contact_data(contact_props, new_data)
        
        payload = {"properties": merged_properties}
        result = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
        print(f"Synced {name} ({phone}) -> HubSpot contact {contact_id}: trial average {average}")
        print(json.dumps(result.get("properties", {}), indent=2))
