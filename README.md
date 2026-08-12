# 🏥 AI-Powered Dynamic Clinical Queue & Triage Management System

An intelligent clinical queue management system that combines Machine Learning, dynamic priority scheduling, starvation prevention, and real-time ETA calculation to improve hospital and OPD queue management.

Traditional hospital queues often use First-In-First-Out (FIFO) scheduling. This can cause emergency patients to wait behind routine patients. This project introduces a dynamic triage-aware queue that prioritizes patients according to urgency while preventing lower-priority patients from waiting indefinitely.

---

## 📌 Problem Statement

Traditional hospital queue systems have several limitations:

* Emergency patients may have to wait behind routine patients.
* Fixed waiting-time estimates can be inaccurate.
* Priority-based queues can cause routine patients to experience starvation.
* Manual queue management can lead to congestion and inefficient workflow.

---

## 💡 Proposed Solution

This system dynamically manages the clinical queue using:

* Clinical urgency-based priority scheduling
* Machine Learning-based consultation duration prediction
* Starvation prevention using an aging algorithm
* Real-time rolling ETA calculation
* Persistent patient and queue storage
* Real-time clinical analytics

---

## ✨ Key Features

### 🤖 1. ML-Based Consultation Duration Prediction
A Random Forest Regressor predicts expected consultation duration using:
* Age
* Blood pressure
* Heart rate
* Urgency tier
* Follow-up status

The trained model is stored as: `duration_predictor.joblib`

---

### 🚨 2. Dynamic Priority Scheduling

| Tier | Category | Priority |
| :--- | :--- | :--- |
| 🔴 **Tier 1** | Emergency / Resuscitation | Highest |
| 🟠 **Tier 2** | Urgent | High |
| 🟡 **Tier 3** | Standard | Medium |
| 🟢 **Tier 4** | Routine / Non-Urgent | Low |

* The queue dynamically sorts patients according to their current priority score.
* Patients within the same urgency tier maintain arrival order.

---

### ⏳ 3. Starvation Prevention
A priority queue can continuously postpone routine patients if emergency cases keep arriving. To prevent this, the system uses an aging algorithm:

$$\text{Aging Boost} = +0.5\text{ tier per 15 minutes of waiting}$$

This gradually increases the effective priority of long-waiting patients.

---

### 🕐 4. Rolling ETA Calculation
The system calculates estimated waiting times using the predicted consultation durations of patients ahead in the queue:

* **Patient A:** Consultation: 10 mins $\to$ **Wait: 0 mins**
* **Patient B:** Consultation: 15 mins $\to$ **Wait: 10 mins**
* **Patient C:** Consultation: 20 mins $\to$ **Wait: 25 mins**

The ETA is recalculated whenever the queue state changes.

---

### 🔔 5. Call Next Patient Workflow

```text
[ WAITING ] ──► [ CALL NEXT PATIENT ] ──► [ IN CONSULTATION ] ──► [ COMPLETED ]
```

The system automatically selects and transitions the highest-priority eligible patient.

## 💾 6. Persistent SQLite Storage
Patient records, triage information, queue status, and operational timestamps are stored in clinic.db. SQLite provides persistent local storage so data is retained across application restarts.

## 📊 7. Real-Time Analytics
The Streamlit dashboard tracks:

Active queue size

Completed consultations

Average consultation duration

Live urgency distribution

Real-time rolling ETAs

Patient queue positions

Clinical throughput

---

## 🏗️ System Architecture
```text

┌───────────────────────────────┐
│       Streamlit Frontend      │
│          Port 8501            │
└───────────────┬───────────────┘
                │
                │ REST API / JSON
                ▼
┌───────────────────────────────┐
│        FastAPI Backend        │
│          Port 8000            │
└───────────────┬───────────────┘
                │
       ┌────────┼────────┐
       │        │        │
       ▼        ▼        ▼
┌──────────┐ ┌────────┐ ┌──────────┐
│ Random   │ │Dynamic │ │ SQLite   │
│ Forest   │ │ Queue  │ │ Database │
│ Predictor│ │ Engine │ │          │
└──────────┘ └────────┘ └──────────┘
```

---

## 🧰 Technology Stack

| Component | Technology |
| :--- | :--- |
| **Programming Language** | Python 3.10+ |
| **Frontend UI** | Streamlit |
| **Backend Framework** | FastAPI, Uvicorn |
| **Machine Learning** | Scikit-learn (Random Forest Regressor) |
| **Data Processing** | Pandas, NumPy |
| **Data Validation** | Pydantic |
| **Model Serialization** | Joblib |
| **Storage & Persistence** | SQLite3 |

---

### 📂 Project Structure

```text
clinical_queue_system/
│
├── main.py                   # FastAPI backend, database operations and queue logic
├── app.py                    # Streamlit frontend and analytics dashboard
├── seed_data.py              # Generates synthetic patient data
├── train_model.py            # Trains the Random Forest model
├── duration_predictor.joblib # Serialized ML model
├── clinic.db                 # SQLite database (auto-generated)
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Installation & Quick Start

**1. Create & Activate Virtual Environment**

* Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.
```

* macOS / Linux
```powershell
# python3 -m venv venv
# source venv/bin/activate
```

**2. Install Dependencies**
```powershell
pip install -r requirements.txt
```
**3. Train the ML Model**
```powershell
python train_model.py
```
**4. Start the Backend (Terminal 1)**
```powershell
uvicorn main:app --reload
```
**Backend API:** http://127.0.0.1:8000

**Swagger API Docs:** http://127.0.0.1:8000/docs

**5. Start the Frontend (Terminal 2)**
```powershell
streamlit run app.py
```
**Dashboard:** http://localhost:8501

# 🧪 Demo & Testing

**1.Seed Synthetic Patients:**
```powersnell
python seed_data.py
```

**2.View Dynamic Queue:** Open http://localhost:8501 and go to 📊 Live Priority Queue to inspect aging boosts, predicted consult durations, and rolling ETAs.

**3.Call Next Patient:** Click 🔔 Call Next Patient to serve the highest-priority patient.

**4.Inspect Analytics:** Open 📈 Clinic Analytics to view completed visits, average durations, and urgency distributions.

**5.Reset Data:** Go to ⚙️ System Controls and select 🗑️ Reset All Queue Data.

---

### 📡 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check and ML model status |
| `POST` | `/api/tokens/issue` | Accepts vitals, predicts duration, and creates patient token |
| `GET` | `/api/queue` | Returns the active dynamic priority queue |
| `POST` | `/api/queue/call-next` | Transitions the next highest-priority patient to completed |
| `GET` | `/api/stats` | Returns aggregate clinical metrics |
| `DELETE` | `/api/queue/reset` | Clears all queue records from the database |
---

### 🚨 Triage Urgency Levels

| Tier | Category | Priority | Target Window | Description / Clinical Indication |
| :--- | :--- | :--- | :--- | :--- |
| 🔴 **Tier 1** | Emergency / Resuscitation | Immediate | 0 minutes | Life-threatening conditions (e.g., cardiac arrest, severe trauma) |
| 🟠 **Tier 2** | Urgent | High | < 15 minutes | Critical vitals, severe acute pain, or rapid deterioration risk |
| 🟡 **Tier 3** | Standard | Medium | < 60 minutes | Moderate symptoms, stable vitals, and general consultations |
| 🟢 **Tier 4** | Routine / Non-Urgent | Low | < 120 minutes | Routine checkups, minor reviews, and follow-up visits |

> **Note:** These tiers are designed for demonstration and educational simulation and do not replace professional medical triage protocols.

---

## 🧠 Queue Processing Workflow
```text
Patient Arrives
       │
       ▼
Collect Patient Data
       │
       ▼
Determine Urgency Tier
       │
       ▼
Predict Consultation Duration
       │
       ▼
Calculate Dynamic Priority
       │
       ▼
Apply Aging Boost
       │
       ▼
Sort Queue
       │
       ▼
Calculate Rolling ETA
       │
       ▼
Call Next Patient
       │
       ▼
Update Queue & Recalculate ETA

🔬 Machine Learning Workflow

Patient Vitals & Profile
       │
       ▼
Feature Extraction
 ├── Age
 ├── Blood Pressure
 ├── Heart Rate
 ├── Urgency Tier
 └── Follow-up Status
       │
       ▼
Random Forest Regressor
       │
       ▼
Predicted Duration (Minutes)
       │
       ▼
Rolling Prefix-Sum Wait Times (ETAs)
```
---

## 📈 Benefits

🚑 Faster prioritization of emergency cases

⏱️ More realistic waiting-time estimates

⚖️ Reduced starvation of routine patients

👨‍⚕️ Better clinical workflow management

📊 Real-time queue visibility and analytics

🔮 Future Enhancements
📱 Patient mobile application & self-check-in

🔔 SMS and WhatsApp queue updates

🏥 Multi-department & multi-doctor routing

🔐 Role-based access control (RBAC)

☁️ Cloud deployment & containerization

🔄 Automated doctor workload balancing

---

## 🔐 Data Privacy
This repository uses a local SQLite database intended for synthetic patient data. A production healthcare deployment requires authentication, authorization, end-to-end encryption, audit logging, and compliance with healthcare data regulations (e.g., HIPAA / DISHA).

---

## ⚠️ Disclaimer
This project is an academic and software engineering prototype demonstrating machine learning, dynamic scheduling, queue optimization, and healthcare workflow simulation. It is not a certified medical device and should not be used to make clinical decisions without validated protocols, clinical testing, and regulatory approval.

---

## 📜 License
This project is licensed under the MIT License.
