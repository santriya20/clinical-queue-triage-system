from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class TokenModel(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_code = Column(String, unique=True, index=True)
    patient_name = Column(String)
    triage_level = Column(Integer)  # 1: Emergency, 2: Urgent, 3: Standard
    visit_type = Column(String)     # "NEW" or "FOLLOW_UP"
    current_stage = Column(String, default="WAITING_DOCTOR")  # WAITING_DOCTOR, IN_LAB, RE_CONSULT, COMPLETED
    entry_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="QUEUED")  # QUEUED, ACTIVE, COMPLETED