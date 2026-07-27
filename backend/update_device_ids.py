"""
Script to update device_id (host_user_id) for all HubSpot contacts by matching with Supabase.
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Import shared HubSpot utilities
from hubspot_utils import (
    supabase_request,
    hubspot_request,
    normalize_phone,
    find_contact_by_phone,
    find_contact_by_email,
)

def update_device_ids():
    """Update device_id for all HubSpot contacts based on Supabase data."""
    print("=" * 60)
    print("UPDATING DEVICE IDs: Supabase → HubSpot")
    print("=" * 60)
    
    # Step 1: Fetch all patients from Supabase
    print("\n[1/3] Fetching all patients from Supabase...")
    try:
        patients = supabase_request("/rest/v1/research_patients", params={
            "select": "id,name,contact,host_user_id,condition",
            "order": "created_at.desc"
        })
        print(f"  Found {len(patients)} patients")
    except Exception as exc:
        print(f"✗ Failed to fetch patients: {exc}")
        return
    
    if not patients:
        print("  No patients found.")
        return
    
    # Step 2: Process each patient and update HubSpot
    print(f"\n[2/3] Updating device IDs in HubSpot...")
    updated = 0
    errors = 0
    skipped = 0
    
    for idx, patient in enumerate(patients, 1):
        patient_id = patient.get("id")
        name = patient.get("name") or ""
        contact = (patient.get("contact") or "").strip()
        host_user_id = patient.get("host_user_id")
        
        if not contact or not host_user_id:
            skipped += 1
            continue
        
        # Determine if contact is email or phone
        email = ""
        phone = ""
        if "@" in contact and "." in contact:
            email = contact
        else:
            phone = normalize_phone(contact)
            if not phone:
                skipped += 1
                continue
        
        # Find contact in HubSpot
        try:
            hubspot_contact_id = None
            
            # Try to find by phone first
            if phone:
                contact_id, _ = find_contact_by_phone(phone)
                if contact_id:
                    hubspot_contact_id = contact_id
            
            # If not found by phone, try by email
            if not hubspot_contact_id and email:
                contact_id, _ = find_contact_by_email(email)
                if contact_id:
                    hubspot_contact_id = contact_id
            
            if not hubspot_contact_id:
                print(f"  [{idx}/{len(patients)}] ⊘ {name}: Not found in HubSpot")
                skipped += 1
                continue
            
            # Update device_id in HubSpot
            update_payload = {
                "properties": {
                    "device_id": str(host_user_id)
                }
            }
            
            hubspot_request(
                f"/crm/v3/objects/contacts/{hubspot_contact_id}",
                method="PATCH",
                payload=update_payload
            )
            
            updated += 1
            print(f"  [{idx}/{len(patients)}] ✓ {name}: device_id = {host_user_id}")
            
        except Exception as exc:
            errors += 1
            print(f"  [{idx}/{len(patients)}] ✗ {name}: {exc}")
    
    # Step 3: Summary
    print(f"\n[3/3] Update Complete!")
    print("=" * 60)
    print(f"✓ Updated: {updated}")
    print(f"⊘ Skipped: {skipped}")
    print(f"✗ Errors: {errors}")
    print("=" * 60)

if __name__ == "__main__":
    update_device_ids()