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


def hubspot_request(path: str, method: str = "GET", payload: dict | None = None, params: dict | None = None) -> dict:
    """Make a request to HubSpot API."""
    if not HUBSPOT_PAT:
        raise RuntimeError("HUBSPOT_PAT not set")
    url = f"https://api.hubapi.com{path}"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_PAT}",
        "Content-Type": "application/json",
    }
    if method == "GET":
        resp = requests.get(url, headers=headers, params=params, timeout=20)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    elif method == "PATCH":
        resp = requests.patch(url, headers=headers, json=payload, timeout=20)
    elif method == "DELETE":
        resp = requests.delete(url, headers=headers, timeout=20)
    else:
        raise RuntimeError("Unsupported method")
    
    if not resp.ok:
        print(f"  HubSpot API Error {resp.status_code}: {resp.text[:500]}")
    
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to E.164 format for HubSpot (+91XXXXXXXXX).
    
    Handles various formats:
    - 9876543210 -> +919876543210
    - +919876543210 -> +919876543210
    - 09876543210 -> +919876543210
    - 919876543210 -> +919876543210
    
    Returns normalized phone number in +91XXXXXXXXX format (NO HYPHENS).
    """
    if not phone:
        return ""
    
    # Remove ALL whitespace, hyphens, parentheses, dots
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    
    # Extract all digits
    digits = re.sub(r'[^\d]', '', cleaned)
    
    # Keep only the last 10 digits (removes any country code or prefix)
    if len(digits) > 10:
        digits = digits[-10:]
    
    # Return in E.164 format: +91XXXXXXXXX (NO HYPHENS)
    return f"+91{digits}"


_contact_properties_cache: set[str] | None = None


def _get_existing_contact_properties() -> set[str]:
    """Fetch existing HubSpot contact property names."""
    try:
        result = hubspot_request("/crm/v3/properties/contacts")
        return {p["name"] for p in result.get("results", [])}
    except Exception:
        return set()


def ensure_contact_properties() -> None:
    """Ensure all custom properties exist in HubSpot.

    Checks existing properties first to avoid 409 Conflict errors
    on every call. Results are cached for the process lifetime.
    """
    global _contact_properties_cache

    if _contact_properties_cache is None:
        _contact_properties_cache = _get_existing_contact_properties()

    existing = _contact_properties_cache

    for name, label, prop_type, field_type in [
        ("dominant_hand", "Dominant Hand", "string", "text"),
        ("patient_code", "Patient Code", "string", "text"),
        ("age", "Age", "number", "number"),
        ("gender", "Gender", "string", "text"),
        ("condition", "Condition", "string", "text"),
        ("test_date", "Test Date", "datetime", "date"),
        ("posture", "Posture", "string", "text"),
        # Hand-specific trial fields (LOWERCASE names required by HubSpot)
        ("left_trial_1", "Left Trial 1", "number", "number"),
        ("left_trial_2", "Left Trial 2", "number", "number"),
        ("left_trial_3", "Left Trial 3", "number", "number"),
        ("left_avg", "Left Average", "number", "number"),
        ("right_trial_1", "Right Trial 1", "number", "number"),
        ("right_trial_2", "Right Trial 2", "number", "number"),
        ("right_trial_3", "Right Trial 3", "number", "number"),
        ("right_avg", "Right Average", "number", "number"),
        # Legacy fields (kept for backward compatibility)
        ("trial_1", "Trial 1", "number", "number"),
        ("trial_2", "Trial 2", "number", "number"),
        ("trial_3", "Trial 3", "number", "number"),
        ("average_trial", "Average Trial", "number", "number"),
        ("average_kg", "Average KG", "number", "number"),
        ("created_at", "Created At", "datetime", "date"),
    ]:
        if name in existing:
            continue
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
            existing.add(name)
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" not in message and "duplicate" not in message and "400" not in message:
                print(f"✗ Error creating property {name}: {exc}")
            else:
                print(f"✓ Property already exists: {name}")
                existing.add(name)


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
            "properties": ["firstname", "lastname", "phone", "email", "last_synced_reading_at"],
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


def find_contact_by_email(email: str) -> tuple[str | None, dict | None]:
    """
    Find a HubSpot contact by email address.
    
    Returns:
        tuple: (contact_id, properties) or (None, None) if not found
    """
    if not email:
        return None, None
    
    search_payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": email,
            }]
        }],
        "properties": ["firstname", "lastname", "phone", "email", "last_synced_reading_at"],
        "limit": 1,
    }
    try:
        result = hubspot_request("/crm/v3/objects/contacts/search", method="POST", payload=search_payload)
        if result.get("results"):
            contact = result["results"][0]
            return contact["id"], contact.get("properties", {})
    except Exception as exc:
        print(f"  Warning: Email search failed for {email}: {exc}")
    
    return None, None


def find_contact_by_name(first_name: str, last_name: str = "") -> tuple[str | None, dict | None]:
    """
    Find a HubSpot contact by name (first and last name).
    Uses partial matching to find similar names.
    
    Returns:
        tuple: (contact_id, properties) or (None, None) if not found
    """
    if not first_name:
        return None, None
    
    # Build name search query
    name_query = f"{first_name} {last_name}".strip()
    
    search_payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "firstname",
                "operator": "CONTAINS_TOKEN",
                "value": first_name,
            }]
        }],
        "properties": ["firstname", "lastname", "phone", "email", "last_synced_reading_at"],
        "limit": 5,  # Get more results to find best match
    }
    
    # Add last name filter if provided
    if last_name:
        search_payload["filterGroups"][0]["filters"].append({
            "propertyName": "lastname",
            "operator": "CONTAINS_TOKEN",
            "value": last_name,
        })
    
    try:
        result = hubspot_request("/crm/v3/objects/contacts/search", method="POST", payload=search_payload)
        if result.get("results"):
            # Return the first match (most relevant)
            contact = result["results"][0]
            return contact["id"], contact.get("properties", {})
    except Exception as exc:
        print(f"  Warning: Name search failed for {name_query}: {exc}")
    
    return None, None


def upsert_contact_by_phone(phone: str, first_name: str, last_name: str = "", email: str = "") -> tuple[str, dict]:
    """
    Find or create a contact by phone number, email, or name.
    This is the MAIN function to use - it ensures no duplicates.
    Uses multiple matching strategies in order of reliability:
    1. Phone number (most reliable)
    2. Email address
    3. Name (least reliable, but useful fallback)
    
    Returns:
        tuple: (contact_id, properties)
    """
    # Strategy 1: Try to find by phone number (most reliable)
    contact_id, contact_props = find_contact_by_phone(phone)
    
    # Strategy 2: If not found by phone, try by email
    if not contact_id and email:
        contact_id, contact_props = find_contact_by_email(email)
    
    # Strategy 3: If not found by email, try by name
    if not contact_id and first_name:
        contact_id, contact_props = find_contact_by_name(first_name, last_name)
    
    if contact_id:
        # Update existing contact with latest info
        update_payload = {
            "properties": {
                "firstname": first_name or contact_props.get("firstname", ""),
                "lastname": last_name or contact_props.get("lastname", ""),
                "phone": phone,
            }
        }
        
        # Add email if provided
        if email:
            update_payload["properties"]["email"] = email
        
        try:
            hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=update_payload)
        except Exception as exc:
            print(f"  Warning: Failed to update contact: {exc}")
        
        return contact_id, contact_props
    
    # Create new contact
    create_payload = {
        "properties": {
            "firstname": first_name,
            "lastname": last_name,
            "phone": phone,
        }
    }
    
    # Add email if provided
    if email:
        create_payload["properties"]["email"] = email
    
    created = hubspot_request("/crm/v3/objects/contacts", method="POST", payload=create_payload)
    return created["id"], created.get("properties", {})


def is_email(contact: str) -> bool:
    """
    Check if a contact string is an email address.
    
    Args:
        contact: String to check
        
    Returns:
        True if the string contains @ symbol (email format)
    """
    if not contact:
        return False
    return "@" in contact and "." in contact


def merge_contact_data(existing_props: dict, new_data: dict) -> dict:
    """
    Merge new data with existing contact data.
    Always updates with new values (no conflict resolution needed).
    
    Filters out HubSpot read-only properties to avoid API errors.
    """
    # HubSpot read-only properties that should not be included in updates
    read_only_properties = {
        # System properties
        "createdate", "lastmodifieddate", "hs_lastmodifieddate",
        "hs_createdate", "hs_object_id", "hs_object_source_id",
        # Engagement properties
        "hs_is_unworked", "hs_num_active_contracts", "hs_num_associated_contacts",
        "hs_num_associated_deals", "hs_num_associated_tickets", "hs_num_associated_quotes",
        "hs_num_associated_calls", "hs_num_associated_emails", "hs_num_associated_meetings",
        "hs_num_associated_notes", "hs_num_associated_tasks",
        # Other read-only properties
        "hs_analytics_num_page_views", "hs_analytics_num_visits",
        "hs_analytics_first_timestamp", "hs_analytics_last_timestamp",
        "hs_analytics_num_event_completions",
    }
    
    # Start with new data (what we want to set)
    merged = dict(new_data)
    
    # Only add existing properties that are not read-only and not in new_data
    for key, value in existing_props.items():
        # Skip read-only properties and properties we're already setting
        if key in read_only_properties or key in new_data:
            continue
        # Only include if it has a value
        if value is not None and value != "":
            merged[key] = value
    
    return merged
