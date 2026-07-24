import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location("backend_main", Path(__file__).with_name("main.py"))
backend_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_main)


def test_build_contact_properties_omits_empty_values():
    payload = {
        "name": "Asha",
        "phone": "9876543210",
        "dominantHand": "Right",
        "patientCode": None,
        "age": 34,
        "testDate": "2026-07-23",
        "posture": "Standing",
        "trial1": 12.5,
        "trial2": 13.2,
        "trial3": 11.8,
        "averageTrial": 12.5,
        "createdAt": "2026-07-23T10:00:00Z",
    }

    properties = backend_main.build_contact_properties(payload)

    assert properties["firstname"] == "Asha"
    assert properties["phone"] == "9876543210"
    assert properties["dominant_hand"] == "Right"
    assert properties["age"] == "34"
    assert properties["patient_code"] is None


def test_build_contact_properties_uses_blank_placeholders_for_missing_values():
    payload = {
        "name": "Asha",
        "phone": "9876543210",
    }

    properties = backend_main.build_contact_properties(payload)

    assert properties["firstname"] == "Asha"
    assert properties["phone"] == "9876543210"
    assert properties["dominant_hand"] is None
    assert properties["patient_code"] is None
    assert properties["age"] is None
    assert properties["test_date"] is None
    assert properties["posture"] is None
    assert properties["trial_1"] is None
    assert properties["trial_2"] is None
    assert properties["trial_3"] is None
    assert properties["average_trial"] is None
    assert properties["created_at"] is None


def test_sync_app_contact_skips_existing_contact(monkeypatch):
    calls = []

    def fake_hubspot_request(path, method="GET", payload=None):
        calls.append((path, method, payload))
        if path == "/crm/v3/objects/contacts/search":
            return {"results": [{"id": "abc123", "properties": {}}]}
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(backend_main, "hubspot_request", fake_hubspot_request)

    result = backend_main.sync_app_contact_to_hubspot({
        "name": "Asha",
        "phone": "9876543210",
    })

    assert result["status"] == "skipped_existing"
    assert len(calls) == 1
