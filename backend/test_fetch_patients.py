"""
Test script to fetch 5 patients from Supabase and display their data
"""
import json
from hubspot_utils import supabase_request

print("=" * 80)
print("FETCHING 5 PATIENTS FROM SUPABASE")
print("=" * 80)

try:
    # Fetch 5 patients with all fields
    patients = supabase_request("/rest/v1/research_patients", params={
        "select": "id,name,contact,age,gender,patient_code,dominant_hand,dob,created_at",
        "order": "created_at.desc",
        "limit": "5"
    })
    
    print(f"\nFound {len(patients)} patients\n")
    
    for idx, patient in enumerate(patients, 1):
        print(f"\n{'='*80}")
        print(f"PATIENT {idx}:")
        print(f"{'='*80}")
        print(f"ID: {patient.get('id')}")
        print(f"Name: {patient.get('name')}")
        print(f"Contact (Phone): {patient.get('contact')}")
        print(f"Age: {patient.get('age')}")
        print(f"Gender: {patient.get('gender')}")
        print(f"Patient Code: {patient.get('patient_code')}")
        print(f"Dominant Hand: {patient.get('dominant_hand')}")
        print(f"DOB: {patient.get('dob')}")
        print(f"Created At: {patient.get('created_at')}")
        
        # Fetch latest reading for this patient
        patient_id = patient.get("id")
        if patient_id:
            readings = supabase_request(
                "/rest/v1/patient_readings",
                params={
                    "select": "trial1,trial2,trial3,hand,posture,assessment_type,created_at",
                    "patient_id": f"eq.{patient_id}",
                    "order": "created_at.desc",
                    "limit": "1"
                }
            )
            
            if readings:
                latest = readings[0]
                print(f"\nLATEST READING:")
                print(f"  Trial 1: {latest.get('trial1')}")
                print(f"  Trial 2: {latest.get('trial2')}")
                print(f"  Trial 3: {latest.get('trial3')}")
                print(f"  Hand: {latest.get('hand')}")
                print(f"  Posture: {latest.get('posture')}")
                print(f"  Assessment Type: {latest.get('assessment_type')}")
                print(f"  Created At: {latest.get('created_at')}")
                
                # Calculate average
                try:
                    trial1 = float(latest.get("trial1", 0))
                    trial2 = float(latest.get("trial2", 0))
                    trial3 = float(latest.get("trial3", 0))
                    average = round((trial1 + trial2 + trial3) / 3, 2)
                    print(f"  Average: {average}")
                except:
                    print(f"  Average: N/A")
    
    print(f"\n{'='*80}")
    print("DATA FETCH COMPLETE")
    print(f"{'='*80}\n")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()