"""
Bulk sync script to upload ALL existing Supabase patient data to HubSpot.
This bypasses the 20-record limit and syncs everything.
Uses normalized phone numbers to prevent duplicates.
"""
import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Import shared HubSpot utilities
from hubspot_utils import (
    supabase_request,
    hubspot_request,
    normalize_phone,
    ensure_contact_properties,
    find_contact_by_phone,
    upsert_contact_by_phone,
)


def ensure_contact_properties() -> None:
    """Ensure all custom properties exist in HubSpot."""
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
        ("average_kg", "Average KG", "number", "number"),
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
            print(f"✓ Created property: {name}")
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" not in message and "duplicate" not in message and "400" not in message:
                print(f"✗ Error creating property {name}: {exc}")
            else:
                print(f"✓ Property already exists: {name}")


def sync_all_patients():
    """Sync ALL patients from Supabase to HubSpot."""
    print("=" * 60)
    print("STARTING BULK SYNC: All Supabase Patients → HubSpot")
    print("=" * 60)
    
    # Step 1: Ensure HubSpot properties exist
    print("\n[1/4] Ensuring HubSpot contact properties exist...")
    ensure_contact_properties()
    
    # Step 2: Fetch ALL patients (no limit)
    print("\n[2/4] Fetching ALL patients from Supabase...")
    try:
        patients = supabase_request("/rest/v1/research_patients", params={
            "select": "id,name,contact",
            "order": "created_at.desc"
        })
        print(f"  Found {len(patients)} total patients")
    except Exception as exc:
        print(f"✗ Failed to fetch patients: {exc}")
        return
    
    if not patients:
        print("  No patients found to sync.")
        return
    
    # Step 3: Process each patient
    print(f"\n[3/4] Processing {len(patients)} patients...")
    synced = []
    skipped = []
    errors = []
    
    for idx, patient in enumerate(patients, 1):
        patient_id = patient.get("id")
        name = patient.get("name") or ""
        contact = (patient.get("contact") or "").strip()
        
        if not patient_id or not contact:
            skipped.append({"patient": name, "reason": "missing_id_or_contact"})
            continue
        
        # Fetch latest reading for this patient
        try:
            readings = supabase_request(
                "/rest/v1/patient_readings",
                params={
                    "select": "trial1,trial2,trial3,hand,posture,assessment_type,created_at",
                    "patient_id": f"eq.{patient_id}",
                    "order": "created_at.desc",
                    "limit": "1"
                }
            )
        except Exception as exc:
            errors.append({"patient": name, "error": f"Failed to fetch readings: {exc}"})
            continue
        
        if not readings:
            skipped.append({"patient": name, "reason": "no_readings"})
            continue
        
        latest = readings[0]
        
        # Extract trial values
        try:
            trial1 = float(latest.get("trial1", 0))
            trial2 = float(latest.get("trial2", 0))
            trial3 = float(latest.get("trial3", 0))
        except Exception:
            skipped.append({"patient": name, "reason": "invalid_trial_data"})
            continue
        
        average = round((trial1 + trial2 + trial3) / 3, 2)
        
        # Normalize phone number
        phone = normalize_phone(contact) if contact else ""
        
        if not phone:
            skipped.append({"patient": name, "reason": "no_valid_phone"})
            continue
        
        # Upsert contact in HubSpot (handles phone normalization)
        try:
            first_name = name.split()[0] if name else "Patient"
            last_name = " ".join(name.split()[1:]) if " " in name else ""
            contact_id, contact_props = upsert_contact_by_phone(phone, first_name, last_name)
        except Exception as exc:
            errors.append({"patient": name, "error": f"Failed to upsert contact: {exc}"})
            continue
        
        latest_created_at = latest.get("created_at")
        
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
                    "trial_readings": {
                        "trial_1": trial1,
                        "trial_2": trial2,
                        "trial_3": trial3
                    },
                    "average_trial": average,
                    "average_kg": average,
                    "hand": latest.get("hand"),
                    "posture": latest.get("posture"),
                    "assessment_type": latest.get("assessment_type"),
                    "created_at": latest_created_at,
                }),
                "last_synced_reading_at": latest_created_at,
            }
        }
        
        # Update contact in HubSpot
        try:
            res = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
            synced.append({
                "patient": name,
                "phone": phone,
                "hubspot_id": contact_id,
                "avg": average,
                "trials": f"{trial1}/{trial2}/{trial3}"
            })
            print(f"  [{idx}/{len(patients)}] ✓ Synced: {name} (Avg: {average})")
        except Exception as exc:
            errors.append({"patient": name, "error": f"Failed to update HubSpot: {exc}"})
            print(f"  [{idx}/{len(patients)}] ✗ Error: {name} - {exc}")
        
        # Small delay to avoid rate limiting
        if idx % 10 == 0:
            time.sleep(1)
    
    # Step 4: Summary
    print("\n[4/4] Sync Complete!")
    print("=" * 60)
    print(f"✓ Successfully synced: {len(synced)}")
    print(f"⊘ Skipped: {len(skipped)}")
    print(f"✗ Errors: {len(errors)}")
    print("=" * 60)
    
    if synced:
        print("\nSynced patients:")
        for s in synced:
            print(f"  - {s['patient']}: Avg {s['avg']} ({s['trials']})")
    
    if errors:
        print("\nErrors:")
        for e in errors[:10]:  # Show first 10 errors
            print(f"  - {e['patient']}: {e['error']}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    return {
        "total_patients": len(patients),
        "synced_count": len(synced),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "synced": synced,
        "skipped": skipped,
        "errors": errors
    }


if __name__ == "__main__":
    if not HUBSPOT_PAT:
        print("ERROR: HUBSPOT_PAT not found in environment variables.")
        print("Please create a .env file with your HubSpot PAT.")
        sys.exit(1)
    
    if not SUPABASE_ANON_KEY:
        print("ERROR: SUPABASE_ANON_KEY not found in environment variables.")
        print("Please create a .env file with your Supabase anon key.")
        sys.exit(1)
    
    result = sync_all_patients()
    
    # Save detailed log
    with open("sync_log.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nDetailed log saved to: sync_log.json")