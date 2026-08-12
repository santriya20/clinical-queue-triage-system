import streamlit as st
import pandas as pd
import requests

# ----------------- PAGE CONFIG -----------------
st.set_page_config(
    page_title="Dynamic Clinical Queue & AI Triage",
    page_icon="🏥",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

st.title("🏥 Dynamic Clinical Queue & AI Triage Management System")
st.markdown("---")

# ----------------- NAVIGATION TABS -----------------
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
                payload = {
                    "patient_name": patient_name,
                    "age": age,
                    "urgency_tier": urgency_tier,
                    "is_followup": is_followup,
                    "systolic_bp": systolic_bp,
                    "heart_rate": heart_rate
                }
                try:
                    response = requests.post(f"{API_URL}/api/tokens/issue", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"Token Issued: **{data['token_id']}** for {data['patient_name']}")
                        st.info(f"Predicted Consultation Duration: **{data['predicted_duration_mins']} mins**")
                    else:
                        st.error(f"Failed to issue token: {response.text}")
                except Exception as e:
                    st.error(f"Cannot reach backend API: {e}")

# ----------------- TAB 2: LIVE QUEUE & AGING -----------------
with tab2:
    st.subheader("Live Priority Queue (Dynamic Preemption & Aging Algorithm)")
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔔 Call Next Patient", type="primary"):
            try:
                call_res = requests.post(f"{API_URL}/api/queue/call-next")
                if call_res.status_code == 200:
                    called_info = call_res.json()["patient"]
                    st.success(f"Now Serving: **{called_info['patient_name']}** ({called_info['token_id']})")
                else:
                    st.warning("No patients currently waiting.")
            except Exception as e:
                st.error(f"Error calling next patient: {e}")
                
    with col_b:
        if st.button("🔄 Refresh Queue"):
            st.rerun()
        
    try:
        res = requests.get(f"{API_URL}/api/queue")
        if res.status_code == 200:
            queue_data = res.json()
            total = queue_data.get("total_waiting", 0)
            st.info(f"Total Patients Waiting in Queue: **{total}**")
            
            records = queue_data.get("queue", [])
            if records:
                df = pd.DataFrame(records)
                
                # Prefix sum: cumulative wait time before patient's turn
                df["cumulative_wait_mins"] = df["predicted_duration_mins"].cumsum().shift(1).fillna(0).round(1)
                
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
        else:
            st.error("Failed to fetch queue data.")
    except Exception as e:
        st.error(f"Could not connect to FastAPI backend: {e}")

# ----------------- TAB 3: CLINIC ANALYTICS -----------------
with tab3:
    st.subheader("Real-Time Clinic Operations & Throughput Analytics")
    
    try:
        stats_res = requests.get(f"{API_URL}/api/stats")
        queue_res = requests.get(f"{API_URL}/api/queue")
        
        if stats_res.status_code == 200 and queue_res.status_code == 200:
            stats = stats_res.json()
            queue_records = queue_res.json().get("queue", [])
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Patients Waiting", stats.get("total_waiting", 0))
            col_m2.metric("Patients Completed", stats.get("total_completed", 0))
            col_m3.metric("Avg Predicted Consult", f"{stats.get('avg_predicted_duration_mins', 0.0)} mins")
            
            st.markdown("### Waiting Queue Distribution by Urgency Tier")
            if queue_records:
                q_df = pd.DataFrame(queue_records)
                tier_counts = q_df["urgency_tier"].value_counts().sort_index()
                tier_labels = {1: "Tier 1 (Resuscitation)", 2: "Tier 2 (Urgent)", 3: "Tier 3 (Standard)", 4: "Tier 4 (Routine)"}
                
                chart_df = pd.DataFrame({
                    "Urgency Category": [tier_labels.get(t, f"Tier {t}") for t in tier_counts.index],
                    "Patient Count": tier_counts.values
                }).set_index("Urgency Category")
                
                st.bar_chart(chart_df)
            else:
                st.write("No active queue data to display charts.")
    except Exception as e:
        st.error(f"Could not load analytics: {e}")

# ----------------- TAB 4: SYSTEM CONTROLS -----------------
with tab4:
    st.subheader("System Administration & Reset")
    st.warning("Resetting the queue will permanently remove all patient records from the SQLite database.")
    
    if st.button("🗑️ Reset All Queue Data", type="secondary"):
        try:
            del_res = requests.delete(f"{API_URL}/api/queue/reset")
            if del_res.status_code == 200:
                st.success("Clinic queue has been completely cleared.")
            else:
                st.error("Failed to reset queue data.")
        except Exception as e:
            st.error(f"Error executing reset command: {e}")