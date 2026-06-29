import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Float, Integer, Uuid
from datetime import datetime
from src.database import Base

class DatasetSLA(Base):
    __tablename__ = "dataset_slas"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), unique=True, nullable=False)
    target_freshness_hours = Column(Integer, default=24, nullable=False)
    target_quality_score = Column(Float, default=95.0, nullable=False)
    compliance_pct = Column(Float, default=100.0, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
