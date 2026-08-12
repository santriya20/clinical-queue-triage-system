import sqlite3
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ----------------- APP & CONFIG -----------------
app = FastAPI(
    title="Clinical Queue & AI Triage Management API",
    description="Dynamic triage token issue, ML duration estimation, and priority aging queue.",
    version="2.0.0"
)

DB_PATH = "clinic.db"
MODEL_PATH = "duration_predictor.joblib"

# Load the trained Random Forest model (fallback to baseline if missing)
try:
    model = joblib.load(MODEL_PATH)
except Exception:
    model = None

# ----------------- DATABASE INITIALIZATION -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT UNIQUE,
            patient_name TEXT,
            age INTEGER,
            urgency_tier INTEGER,
            is_followup INTEGER,
            systolic_bp INTEGER,
            heart_rate INTEGER,
            predicted_duration_mins REAL,
            status TEXT DEFAULT 'WAITING',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------- PYDANTIC SCHEMAS -----------------
class PatientCreate(BaseModel):
    patient_name: str = Field(..., example="John Doe")
    age: int = Field(..., ge=1, le=120, example=35)
    urgency_tier: int = Field(..., ge=1, le=4, example=2, description="1=Emergency, 2=Urgent, 3=Standard, 4=Routine")
    is_followup: bool = Field(default=False)
    systolic_bp: int = Field(default=120, ge=60, le=240)
    heart_rate: int = Field(default=75, ge=30, le=220)

# ----------------- PRIORITY AGING ALGORITHM -----------------
def calculate_effective_priority(record: dict) -> float:
    """
    Prevents queue starvation:
    Lower effective score = higher priority in the queue.
    For every 15 minutes a patient waits, their priority improves by 0.5 tiers.
    """
    created_at = datetime.fromisoformat(record["created_at"])
    wait_time_minutes = (datetime.utcnow() - created_at).total_seconds() / 60.0
    aging_boost = (wait_time_minutes / 15.0) * 0.5
    
    # Base urgency_tier minus aging boost
    effective_score = record["urgency_tier"] - aging_boost
    return round(effective_score, 3)

# ----------------- API ENDPOINTS -----------------

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/tokens/issue")
def issue_token(patient: PatientCreate):
    # Predict consultation duration using Random Forest
    if model is not None:
        try:
            features = pd.DataFrame([{
                "age": patient.age,
                "urgency_tier": patient.urgency_tier,
                "is_followup": 1 if patient.is_followup else 0,
                "systolic_bp": patient.systolic_bp,
                "heart_rate": patient.heart_rate
            }])
            pred = float(model.predict(features)[0])
            pred_duration = round(max(5.0, min(pred, 60.0)), 1)
        except Exception:
            pred_duration = {1: 30.0, 2: 20.0, 3: 15.0, 4: 10.0}.get(patient.urgency_tier, 15.0)
    else:
        pred_duration = {1: 30.0, 2: 20.0, 3: 15.0, 4: 10.0}.get(patient.urgency_tier, 15.0)

    now_iso = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Generate incremental token
    cursor.execute("SELECT COUNT(*) FROM patients")
    count = cursor.fetchone()[0] + 1
    token_id = f"TKN-{count:04d}"

    cursor.execute("""
        INSERT INTO patients (
            token_id, patient_name, age, urgency_tier, is_followup,
            systolic_bp, heart_rate, predicted_duration_mins, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'WAITING', ?)
    """, (
        token_id, patient.patient_name, patient.age, patient.urgency_tier,
        1 if patient.is_followup else 0, patient.systolic_bp, patient.heart_rate,
        pred_duration, now_iso
    ))
    conn.commit()
    conn.close()

    return {
        "token_id": token_id,
        "patient_name": patient.patient_name,
        "urgency_tier": patient.urgency_tier,
        "predicted_duration_mins": pred_duration,
        "status": "WAITING",
        "created_at": now_iso
    }

@app.get("/api/queue")
def get_queue():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE status = 'WAITING'")
    rows = cursor.fetchall()
    conn.close()

    records = [dict(row) for row in rows]

    # Calculate effective priority with aging boost for each patient
    for r in records:
        r["effective_priority"] = calculate_effective_priority(r)

    # Sort queue: primary key = effective_priority (ascending), secondary key = created_at (FIFO)
    sorted_queue = sorted(records, key=lambda x: (x["effective_priority"], x["created_at"]))

    return {
        "total_waiting": len(sorted_queue),
        "queue": sorted_queue
    }

@app.post("/api/queue/call-next")
def call_next():
    queue_data = get_queue()
    active_queue = queue_data["queue"]

    if not active_queue:
        raise HTTPException(status_code=404, detail="No patients waiting in queue.")

    next_patient = active_queue[0]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE patients SET status = 'COMPLETED' WHERE token_id = ?", (next_patient["token_id"],))
    conn.commit()
    conn.close()

    return {
        "message": "Patient called successfully",
        "patient": next_patient
    }

@app.get("/api/stats")
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM patients WHERE status = 'WAITING'")
    waiting_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM patients WHERE status = 'COMPLETED'")
    completed_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(predicted_duration_mins) FROM patients WHERE status = 'WAITING'")
    avg_duration = cursor.fetchone()[0]
    avg_duration = round(avg_duration, 1) if avg_duration else 0.0

    conn.close()

    return {
        "total_waiting": waiting_count,
        "total_completed": completed_count,
        "avg_predicted_duration_mins": avg_duration
    }

@app.delete("/api/queue/reset")
def reset_queue():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients")
    conn.commit()
    conn.close()
    return {"message": "All queue data successfully reset."}