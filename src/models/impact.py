import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Integer
from datetime import datetime
from src.database import Base

class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(String, nullable=False) # e.g. schema_change, metadata_update
    affected_datasets = Column(String, nullable=False) # JSON-serialized list of affected dataset IDs
    affected_reports = Column(Integer, default=0, nullable=False)
    risk_score = Column(String, nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
