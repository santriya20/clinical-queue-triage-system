import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib

# 1. Generate realistic clinical baseline data
np.random.seed(42)
n_samples = 2500

age = np.random.randint(1, 90, size=n_samples)
triage_tier = np.random.choice([1, 2, 3, 4], size=n_samples, p=[0.1, 0.25, 0.45, 0.2])
is_followup = np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3])
systolic_bp = np.random.normal(120, 15, size=n_samples).astype(int)
heart_rate = np.random.normal(75, 12, size=n_samples).astype(int)

# Urgency baselines: Tier 1=25m, Tier 2=18m, Tier 3=10m, Tier 4=6m
base_duration = {1: 25, 2: 18, 3: 10, 4: 6}
duration = [
    base_duration[t] + (0.05 * a) - (2.5 if f == 1 else 0) + np.random.normal(0, 2)
    for t, a, f in zip(triage_tier, age, is_followup)
]
duration = np.clip(duration, 3, 45)

df = pd.DataFrame({
    'age': age,
    'triage_tier': triage_tier,
    'is_followup': is_followup,
    'systolic_bp': systolic_bp,
    'heart_rate': heart_rate,
    'duration_mins': duration
})

# 2. Train Regressor
X = df[['age', 'triage_tier', 'is_followup', 'systolic_bp', 'heart_rate']]
y = df['duration_mins']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 3. Save Artifact
joblib.dump(model, 'duration_predictor.joblib')
print("SUCCESS: 'duration_predictor.joblib' has been trained and saved!")
