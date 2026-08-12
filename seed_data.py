import requests
import time

API_URL = "http://127.0.0.1:8000/api/tokens/issue"

patients = [
    {"patient_name": "Alice Johnson", "age": 72, "urgency_tier": 1, "is_followup": False, "systolic_bp": 175, "heart_rate": 118},
    {"patient_name": "Bob Smith", "age": 45, "urgency_tier": 3, "is_followup": False, "systolic_bp": 122, "heart_rate": 74},
    {"patient_name": "Charlie Davis", "age": 29, "urgency_tier": 2, "is_followup": False, "systolic_bp": 145, "heart_rate": 95},
    {"patient_name": "Diana Prince", "age": 58, "urgency_tier": 4, "is_followup": True, "systolic_bp": 118, "heart_rate": 70},
    {"patient_name": "Evan Wright", "age": 34, "urgency_tier": 2, "is_followup": False, "systolic_bp": 150, "heart_rate": 98}
]

for p in patients:
    try:
        res = requests.post(API_URL, json=p)
        if res.status_code == 200:
            print(f"Issued Token for {p['patient_name']}: {res.json()['token_id']}")
    except Exception as e:
        print(f"Error seeding {p['patient_name']}: {e}")