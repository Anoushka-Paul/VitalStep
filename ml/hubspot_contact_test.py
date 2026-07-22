import json
import os
import sys
import urllib.request
import urllib.error


def create_contact(properties: dict) -> dict:
    pat = os.getenv("HUBSPOT_PAT")
    if not pat:
        raise RuntimeError("Set the HUBSPOT_PAT environment variable before running this script.")

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    payload = {"properties": properties}

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(f"HubSpot API request failed ({exc.code}): {error_body}") from exc


if __name__ == "__main__":
    sample_data = {
        "firstname": "Rahul",
        "lastname": "Dummy",
        "phone": "9876543210",
        "email": "rahul.dummy+hubspot@example.com",
    }

    print("Sending test contact to HubSpot...")
    print(json.dumps(sample_data, indent=2))

    try:
        result = create_contact(sample_data)
        print("\nHubSpot response:")
        print(json.dumps(result, indent=2))
        print("\n✅ Contact creation request succeeded.")
    except Exception as exc:
        print(f"\n❌ Request failed: {exc}")
        sys.exit(1)
