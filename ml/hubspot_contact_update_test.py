import json
import os
import sys
import urllib.request
import urllib.error


def hubspot_request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    pat = os.getenv("HUBSPOT_PAT")
    if not pat:
        raise RuntimeError("Set the HUBSPOT_PAT environment variable before running this script.")

    url = f"https://api.hubapi.com{path}"
    body = None
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"HubSpot API request failed ({exc.code}): {error_body}") from exc


def ensure_property(name: str, label: str, prop_type: str, field_type: str) -> None:
    payload = {
        "name": name,
        "label": label,
        "type": prop_type,
        "fieldType": field_type,
        "groupName": "contactinformation",
    }
    try:
        hubspot_request("/crm/v3/properties/contacts", method="POST", payload=payload)
        print(f"Created custom property: {name}")
    except RuntimeError as exc:
        if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
            print(f"Property already exists: {name}")
        else:
            raise


if __name__ == "__main__":
    contact_id = os.getenv("HUBSPOT_CONTACT_ID", "523223398115")
    first_name = os.getenv("HUBSPOT_CONTACT_NAME", "Arya")

    ensure_property("trial_1", "Trial 1", "number", "number")
    ensure_property("trial_2", "Trial 2", "number", "number")
    ensure_property("trial_notes", "Trial Notes", "string", "text")
    ensure_property("app_data_json", "App Data JSON", "string", "text")

    payload = {
        "properties": {
            "firstname": first_name,
            "phone": "1122334455",
            "trial_1": 72,
            "trial_2": 68,
            "trial_notes": "app_data_test_from_script",
            "app_data_json": json.dumps({
                "patient_name": first_name,
                "trial_readings": {"trial_1": 72, "trial_2": 68},
                "source": "vitalstep_test"
            }),
        }
    }

    print(f"Updating contact {contact_id} with trial reading values...")
    result = hubspot_request(f"/crm/v3/objects/contacts/{contact_id}", method="PATCH", payload=payload)
    print(json.dumps(result, indent=2))
    print("\n✅ Contact update request succeeded.")
