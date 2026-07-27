"""
Bulk sync script to upload ALL existing Supabase patient data to HubSpot.
This bypasses the 20-record limit and syncs everything.
Uses phone+email deduplication to prevent duplicates.
Sends webhook notification after each sync.
"""
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Import shared HubSpot utilities
from hubspot_utils import (
    supabase_request,
    hubspot_request,
    normalize_phone,
    ensure_contact_properties,
    find_contact_by_phone,
    find_contact_by_email,
    upsert_contact_by_phone,
)

# Webhook configuration
HUBSPOT_WEBHOOK_URL = "https://api.hubapi.com/automation/v4/webhook-triggers/246752206/eErzGjs"


def is_email(contact: str) -> bool:
    """Check if the contact string is an email address."""
    if not contact:
        return False
    return "@" in contact and "." in contact


def send_webhook_notification(patient_data: dict):
    """Send webhook notification to HubSpot after successful sync."""
    try:
        response = requests.post(
            HUBSPOT_WEBHOOK_URL,
            json=patient_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.ok:
            print(f"  ✓ Webhook sent successfully")
        else:
            print(f"  ⚠ Webhook failed: {response.status_code}")
    except Exception as exc:
        print(f"  ⚠ Webhook error: {exc}")


def sync_all_patients():
    """Sync ALL patients from Supabase to HubSpot."""
    print("=" * 60)
    print("STARTING BULK SYNC: All Supabase Patients → HubSpot")
    print("=" * 60)
    
    # Step 1: Ensure HubSpot properties exist
    print("\n[1/4] Ensuring HubSpot contact properties exist...")
    ensure_contact_properties()
    
    # Step 2: Fetch ALL patients with all required fields
    print("\n[2/4] Fetching ALL patients from Supabase...")
    try:
        patients = supabase_request("/rest/v1/research_patients", params={
            "select": "id,name,contact,age,gender,patient_code,dominant_hand,condition,dob,created_at,host_user_id",
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
        
        # Determine if contact is email or phone
        email = ""
        phone = ""
        if is_email(contact):
            email = contact
            print(f"  [{idx}/{len(patients)}] ℹ {name}: Contact is email ({contact})")
        else:
            phone = normalize_phone(contact)
            if not phone:
                skipped.append({"patient": name, "reason": "no_valid_phone"})
                continue
            print(f"  [{idx}/{len(patients)}] ℹ {name}: Contact is phone ({contact} -> {phone})")
        
        # Fetch ALL readings for this patient (to group by hand)
        try:
            all_readings = supabase_request(
                "/rest/v1/patient_readings",
                params={
                    "select": "trial1,trial2,trial3,hand,posture,assessment_type,created_at",
                    "patient_id": f"eq.{patient_id}",
                    "order": "created_at.desc"
                }
            )
        except Exception as exc:
            errors.append({"patient": name, "error": f"Failed to fetch readings: {exc}"})
            continue
        
        # Get condition from patient data
        condition = patient.get("condition", "") or ""
        
        if not all_readings:
            skipped.append({"patient": name, "reason": "no_readings"})
            continue
        
        # Group readings by hand
        left_readings = []
        right_readings = []
        for reading in all_readings:
            hand_type = reading.get("hand", "").lower()
            if hand_type == "left":
                left_readings.append(reading)
            elif hand_type == "right":
                right_readings.append(reading)
        
        # Calculate averages for each hand
        def calculate_average(readings):
            if not readings:
                return None
            try:
                trials = [float(r.get("trial1", 0)) for r in readings]
                return round(sum(trials) / len(trials), 2)
            except:
                return None
        
        left_avg = calculate_average(left_readings)
        right_avg = calculate_average(right_readings)
        
        # Get latest reading for metadata (posture, etc.)
        latest = all_readings[0]
        
        # Upsert contact in HubSpot (handles deduplication by phone/email/name)
        try:
            first_name = name.split()[0] if name else "Patient"
            last_name = " ".join(name.split()[1:]) if " " in name else ""
            contact_id, contact_props = upsert_contact_by_phone(phone, first_name, last_name, email)
        except Exception as exc:
            errors.append({"patient": name, "error": f"Failed to upsert contact: {exc}"})
            continue
        
        latest_created_at = latest.get("created_at")
        
        # Build payload with hand-specific trial fields
        properties = {
            "firstname": first_name,
            "lastname": last_name,
            # Device ID
            "device_id": patient.get("host_user_id"),
            # Posture
            "posture": latest.get("posture"),
            # Metadata
            "trial_source": "supabase_patient_reading",
            "trial_payload_json": json.dumps({
                "patient_name": name,
                "patient_code": patient.get("patient_code"),
                "age": patient.get("age"),
                "gender": patient.get("gender"),
                "dominant_hand": patient.get("dominant_hand"),
                "device_id": patient.get("host_user_id"),
                "trial_readings": {
                    "left_trials": f"{left_readings[0].get('trial1', '')}/{left_readings[0].get('trial2', '')}/{left_readings[0].get('trial3', '')}" if left_readings else "N/A",
                    "right_trials": f"{right_readings[0].get('trial1', '')}/{right_readings[0].get('trial2', '')}/{right_readings[0].get('trial3', '')}" if right_readings else "N/A"
                },
                "left_avg": left_avg,
                "right_avg": right_avg,
                "hand": latest.get("hand"),
                "posture": latest.get("posture"),
                "assessment_type": latest.get("assessment_type"),
                "created_at": latest_created_at,
            }),
            "last_synced_reading_at": latest_created_at,
        }
        
        # Add hand-specific trial fields (left_* and right_* - LOWERCASE for HubSpot)
        # Left hand trials
        if left_readings:
            properties["left_trial_1"] = str(left_readings[0].get("trial1", ""))
            properties["left_trial_2"] = str(left_readings[0].get("trial2", ""))
            properties["left_trial_3"] = str(left_readings[0].get("trial3", ""))
            if left_avg:
                properties["left_avg"] = str(left_avg)
        else:
            # Leave empty if no left hand readings
            properties["left_trial_1"] = ""
            properties["left_trial_2"] = ""
            properties["left_trial_3"] = ""
            properties["left_avg"] = ""
        
        # Right hand trials
        if right_readings:
            properties["right_trial_1"] = str(right_readings[0].get("trial1", ""))
            properties["right_trial_2"] = str(right_readings[0].get("trial2", ""))
            properties["right_trial_3"] = str(right_readings[0].get("trial3", ""))
            if right_avg:
                properties["right_avg"] = str(right_avg)
        else:
            # Leave empty if no right hand readings
            properties["right_trial_1"] = ""
            properties["right_trial_2"] = ""
            properties["right_trial_3"] = ""
            properties["right_avg"] = ""
        
        # Add phone if available
        if phone:
            properties["phone"] = phone
        
        # Add email if available
        if email:
            properties["email"] = email
        
        # Add optional fields only if they have values
        if patient.get("age"):
            properties["age"] = str(patient.get("age"))
        if patient.get("gender"):
            properties["gender"] = patient.get("gender")
        if patient.get("patient_code"):
            properties["patient_code"] = patient.get("patient_code")
        if patient.get("dominant_hand"):
            properties["dominant_hand"] = patient.get("dominant_hand")
        if condition:
            properties["condition"] = condition
        if patient.get("dob"):
            properties["test_date"] = patient.get("dob")
        if patient.get("created_at"):
            properties["created_at"] = patient.get("created_at")
        
        payload = {"properties": properties}
        
        # Update contact in HubSpot
        try:
            res = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
            
            # Send webhook notification
            webhook_data = {
                "patient_name": name,
                "hubspot_contact_id": contact_id,
                "phone": phone,
                "email": email,
                "left_avg": left_avg,
                "right_avg": right_avg,
                "sync_status": "success"
            }
            send_webhook_notification(webhook_data)
            
            synced.append({
                "patient": name,
                "phone": phone,
                "email": email,
                "hubspot_id": contact_id,
                "left_avg": left_avg,
                "right_avg": right_avg,
                "left_trials": f"{left_readings[0].get('trial1', '')}/{left_readings[0].get('trial2', '')}/{left_readings[0].get('trial3', '')}" if left_readings else "N/A",
                "right_trials": f"{right_readings[0].get('trial1', '')}/{right_readings[0].get('trial2', '')}/{right_readings[0].get('trial3', '')}" if right_readings else "N/A",
                "age": patient.get("age"),
                "gender": patient.get("gender"),
                "device_id": patient.get("host_user_id")
            })
            print(f"  [{idx}/{len(patients)}] ✓ Synced: {name} (L:{left_avg or 'N/A'} R:{right_avg or 'N/A'})")
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
            print(f"  - {s['patient']}: L:{s.get('left_avg', 'N/A')} R:{s.get('right_avg', 'N/A')}, Age: {s.get('age')}, Device: {s.get('device_id')}")
    
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
    result = sync_all_patients()
    
    # Save detailed log
    with open("sync_log.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nDetailed log saved to: sync_log.json")
