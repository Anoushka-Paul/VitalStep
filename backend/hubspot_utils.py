"""
HubSpot utility functions with phone number normalization and proper merge logic.
This module ensures no duplicate contacts are created by normalizing phone numbers
and always updating existing contacts.
"""
import re
import json
import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cbebmpgsbxqdzpfgqulj.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
HUBSPOT_PAT = os.getenv("HUBSPOT_PAT")


def supabase_request(path: str, params: dict | None = None) -> list:
    """Make a GET request to Supabase REST API."""
    query = ""
    if params:
        query = "?" + urlencode(params)
    url = f"{SUPABASE_URL}{path}{query}"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


def hubspot_request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    """Make a request to HubSpot API."""
    if not HUBSPOT_PAT:
        raise RuntimeError("HUBSPOT_PAT not set")
    url = f"https://api.hubapi.com{path}"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_PAT}",
        "Content-Type": "application/json",
    }
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=20)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    elif method == "PATCH":
        resp = requests.patch(url, headers=headers, json=payload, timeout=20)
    else:
        raise RuntimeError("Unsupported method")
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to 10 digits only.
    Removes all formatting, country codes, and extra digits.
    Handles various formats:
    - +91-9876543210 -> 9876543210
    - 98765-43210 -> 9876543210
    - +91 9876543210 -> 9876543210
    - 9876543210 -> 9876543210
    - 919876543210 -> 9876543210
    - 09876543210 -> 9876543210
    - +1-987-654-3210 -> 9876543210
    
    Returns normalized phone number (10 digits only).
    """
    if not phone:
        return ""
    
    # Remove all whitespace, hyphens, parentheses, dots
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    
    # Extract all digits
    digits = re.sub(r'[^\d]', '', cleaned)
    
    # Keep only the last 10 digits (removes any country code or prefix)
    if len(digits) > 10:
        digits = digits[-10:]
    
    # Return only 10 digits
    return digits


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


def find_contact_by_phone(phone: str) -> tuple[str | None, dict | None]:
    """
    Find a HubSpot contact by phone number.
    Uses multiple search strategies to handle different phone formats.
    
    Returns:
        tuple: (contact_id, properties) or (None, None) if not found
    """
    normalized = normalize_phone(phone)
    
    # Strategy: Search with normalized 10-digit phone and original format
    search_variants = [
        normalized,  # e.g., 9876543210 (10 digits)
        phone,       # Original format
    ]
    
    # Try each variant
    for search_phone in search_variants:
        if not search_phone:
            continue
            
        search_payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "phone",
                    "operator": "EQ",
                    "value": search_phone,
                }]
            }],
            "properties": ["firstname", "lastname", "phone", "last_synced_reading_at"],
            "limit": 1,
        }
        try:
            result = hubspot_request("/crm/v3/objects/contacts/search", method="POST", payload=search_payload)
            if result.get("results"):
                contact = result["results"][0]
                return contact["id"], contact.get("properties", {})
        except Exception as exc:
            print(f"  Warning: Search failed for {search_phone}: {exc}")
    
    return None, None


def upsert_contact_by_phone(phone: str, first_name: str, last_name: str = "") -> tuple[str, dict]:
    """
    Find or create a contact by phone number.
    This is the MAIN function to use - it ensures no duplicates.
    
    Returns:
        tuple: (contact_id, properties)
    """
    # Try to find existing contact
    contact_id, contact_props = find_contact_by_phone(phone)
    
    if contact_id:
        # Update existing contact with name if provided
        if first_name or last_name:
            update_payload = {
                "properties": {
                    "firstname": first_name or contact_props.get("firstname", ""),
                    "lastname": last_name or contact_props.get("lastname", ""),
                }
            }
            try:
                hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=update_payload)
            except Exception as exc:
                print(f"  Warning: Failed to update contact name: {exc}")
        
        return contact_id, contact_props
    
    # Create new contact
    create_payload = {
        "properties": {
            "firstname": first_name,
            "lastname": last_name,
            "phone": phone,
        }
    }
    created = hubspot_request("/crm/v3/objects/contacts", method="POST", payload=create_payload)
    return created["id"], created.get("properties", {})


def merge_contact_data(existing_props: dict, new_data: dict) -> dict:
    """
    Merge new data with existing contact data.
    Always updates with new values (no conflict resolution needed).
    """
    merged = dict(existing_props)
    
    # Update with new data
    for key, value in new_data.items():
        if value is not None and value != "":
            merged[key] = value
    
    return merged