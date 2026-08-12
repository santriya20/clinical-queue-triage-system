import streamlit as st
import pandas as pd
import numpy as np
import datetime
import joblib
import os
import sqlite3

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Dynamic Clinical Queue & AI Triage",
    page_icon="🏥",
    layout="wide"
)

# ----------------- DATABASE SETUP -----------------
DB_FILE = "clinical_queue.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT UNIQUE,
            patient_name TEXT,
            age INTEGER,
            urgency_tier INTEGER,
            systolic_bp INTEGER,
            heart_rate INTEGER,
            is_followup INTEGER,
            predicted_duration_mins REAL,
            arrival_time TIMESTAMP,
            status TEXT,
            effective_priority REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------- LOAD ML MODEL -----------------
@st.cache_resource
def load_model():
    if os.path.exists("duration_predictor.joblib"):
        return joblib.load("duration_predictor.joblib")
    return None

model_bundle = load_model()

def predict_duration(age, tier):
    if model_bundle:
        try:
            model = model_bundle["model"]
            cols = model_bundle["feature_columns"]
            input_data = pd.DataFrame(0, index=[0], columns=cols)
            if "triage_score" in cols:
                input_data["triage_score"] = tier
            if "age" in cols:
                input_data["age"] = age
            pred = model.predict(input_data)[0]
            return round(float(pred), 1)
        except Exception:
            pass
    # Standard heuristic fallback
    return round(12.0 + (5 - tier) * 3.5, 1)

def compute_priority(tier, bp, hr, arrival_time_dt):
    tier_weights = {1: 100.0, 2: 75.0, 3: 50.0, 4: 25.0}
    base = tier_weights.get(tier, 25.0)
    
    # Vitals anomaly delta
    vitals_score = 0.0
    if bp >= 180 or bp <= 90:
        vitals_score += 15.0
    if hr >= 120 or hr <= 50:
        vitals_score += 10.0
        
    # Aging / Anti-starvation boost: +0.75 score per minute in queue
    wait_minutes = max(0.0, (datetime.datetime.now() - arrival_time_dt).total_seconds() / 60.0)
    starvation_boost = wait_minutes * 0.75
    
    return round(base + vitals_score + starvation_boost, 2)

# ----------------- UI HEADER -----------------
st.title("🏥 Dynamic Clinical Queue & AI Triage Management System")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Patient Triage & Token Issue",
    "📊 Live Priority Queue",
    "📈 Clinic Analytics",
    "⚙️ System Controls"
])

# ----------------- TAB 1: TOKEN ISSUANCE -----------------
with tab1:
    st.subheader("Patient Intake & Vital Registration")
    
    with st.form("patient_registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            patient_name = st.text_input("Patient Full Name", placeholder="e.g. John Doe")
            age = st.number_input("Age", min_value=1, max_value=120, value=35)
            urgency_tier = st.selectbox(
                "Triage Urgency Category",
                options=[1, 2, 3, 4],
                format_func=lambda x: {
                    1: "Tier 1 - Resuscitation / Immediate Emergency",
                    2: "Tier 2 - Urgent / Critical Vitals",
                    3: "Tier 3 - Standard / General Consultation",
                    4: "Tier 4 - Non-Urgent / Routine Follow-up"
                }[x]
            )
            
        with col2:
            is_followup = st.checkbox("Is this a follow-up review visit?", value=False)
            systolic_bp = st.slider("Systolic Blood Pressure (mmHg)", min_value=60, max_value=240, value=120)
            heart_rate = st.slider("Heart Rate (BPM)", min_value=30, max_value=220, value=75)
            
        submitted = st.form_submit_button("Generate Priority Token", type="primary")
        
        if submitted:
            if not patient_name.strip():
                st.error("Please enter a valid patient name.")
            else:
                arrival = datetime.datetime.now()
                token_id = f"TKN-{arrival.strftime('%H%M%S')}-{np.random.randint(100, 999)}"
                pred_duration = predict_duration(age, urgency_tier)
                priority = compute_priority(urgency_tier, systolic_bp, heart_rate, arrival)
                
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO patients (
                        token_id, patient_name, age, urgency_tier, systolic_bp,
                        heart_rate, is_followup, predicted_duration_mins, arrival_time,
                        status, effective_priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'WAITING', ?)
                """, (token_id, patient_name, age, urgency_tier, systolic_bp, heart_rate, int(is_followup), pred_duration, arrival.isoformat(), priority))
                conn.commit()
                conn.close()
                
                st.success(f"Token Issued: **{token_id}** for {patient_name}")
                st.info(f"Predicted Consultation Duration: **{pred_duration} mins**")

# ----------------- TAB 2: LIVE QUEUE & AGING -----------------
with tab2:
    st.subheader("Live Priority Queue (Dynamic Preemption & Aging Algorithm)")
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔔 Call Next Patient", type="primary"):
            conn = get_db_connection()
            df_wait = pd.read_sql_query("SELECT * FROM patients WHERE status = 'WAITING'", conn)
            if not df_wait.empty:
                df_wait["arrival_dt"] = pd.to_datetime(df_wait["arrival_time"])
                df_wait["effective_priority"] = df_wait.apply(
                    lambda r: compute_priority(r["urgency_tier"], r["systolic_bp"], r["heart_rate"], r["arrival_dt"]),
                    axis=1
                )
                top_patient = df_wait.sort_values(by="effective_priority", ascending=False).iloc[0]
                conn.execute("UPDATE patients SET status = 'COMPLETED' WHERE token_id = ?", (top_patient["token_id"],))
                conn.commit()
                st.success(f"Now Serving: **{top_patient['patient_name']}** ({top_patient['token_id']})")
            else:
                st.warning("No patients currently waiting.")
            conn.close()
            
    with col_b:
        if st.button("🔄 Refresh Queue"):
            st.rerun()
        
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM patients WHERE status = 'WAITING'", conn)
    conn.close()
    
    if not df.empty:
        df["arrival_dt"] = pd.to_datetime(df["arrival_time"])
        df["effective_priority"] = df.apply(
            lambda r: compute_priority(r["urgency_tier"], r["systolic_bp"], r["heart_rate"], r["arrival_dt"]),
            axis=1
        )
        df = df.sort_values(by="effective_priority", ascending=False).reset_index(drop=True)
        df["cumulative_wait_mins"] = df["predicted_duration_mins"].cumsum().shift(1).fillna(0).round(1)
        
        st.info(f"Total Patients Waiting in Queue: **{len(df)}**")
        display_df = df[[
            "token_id", "patient_name", "urgency_tier", "effective_priority",
            "predicted_duration_mins", "cumulative_wait_mins", "status"
        ]].rename(columns={
            "token_id": "Token ID",
            "patient_name": "Patient Name",
            "urgency_tier": "Base Urgency",
            "effective_priority": "Effective Score (Aging Boost)",
            "predicted_duration_mins": "ML Consult Time (mins)",
            "cumulative_wait_mins": "Est. Wait Before Turn (mins)",
            "status": "Status"
        })
        st.dataframe(display_df, use_container_width=True)
    else:
        st.write("No patients currently in the queue.")

# ----------------- TAB 3: CLINIC ANALYTICS -----------------
with tab3:
    st.subheader("Real-Time Clinic Operations & Throughput Analytics")
    conn = get_db_connection()
    all_df = pd.read_sql_query("SELECT * FROM patients", conn)
    conn.close()
    
    if not all_df.empty:
        waiting_count = len(all_df[all_df["status"] == "WAITING"])
        completed_count = len(all_df[all_df["status"] == "COMPLETED"])
        avg_dur = round(float(all_df["predicted_duration_mins"].mean()), 1)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Patients Waiting", waiting_count)
        col_m2.metric("Patients Completed", completed_count)
        col_m3.metric("Avg Predicted Consult", f"{avg_dur} mins")
        
        st.markdown("### Waiting Queue Distribution by Urgency Tier")
        waiting_df = all_df[all_df["status"] == "WAITING"]
        if not waiting_df.empty:
            tier_counts = waiting_df["urgency_tier"].value_counts().sort_index()
            tier_labels = {1: "Tier 1 (Resuscitation)", 2: "Tier 2 (Urgent)", 3: "Tier 3 (Standard)", 4: "Tier 4 (Routine)"}
            chart_df = pd.DataFrame({
                "Urgency Category": [tier_labels.get(t, f"Tier {t}") for t in tier_counts.index],
                "Patient Count": tier_counts.values
            }).set_index("Urgency Category")
            st.bar_chart(chart_df)
        else:
            st.write("No active waiting queue data to display chart.")
    else:
        st.write("No patient records available yet.")

# ----------------- TAB 4: SYSTEM CONTROLS -----------------
with tab4:
    st.subheader("System Administration & Reset")
    st.warning("Resetting the queue will permanently remove all patient records from the SQLite database.")
    
    if st.button("🗑️ Reset All Queue Data", type="secondary"):
        conn = get_db_connection()
        conn.execute("DELETE FROM patients")
        conn.commit()
        conn.close()
        st.success("Clinic queue has been completely cleared.")
        st.rerun()
