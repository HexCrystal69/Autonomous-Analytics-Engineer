import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Uuid, JSON
from datetime import datetime
from src.database import Base

class RootCauseAnalysis(Base):
    __tablename__ = "root_cause_analyses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    issue_type = Column(String, nullable=False) # quality, anomaly, drift, health
    root_cause_category = Column(String, nullable=False) # e.g., missing_data, distribution_shift
    confidence_score = Column(Float, nullable=False)
    analysis_json = Column(JSON, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
