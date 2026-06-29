import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DataQualityRule(Base):
    __tablename__ = "data_quality_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False) # e.g. NULL_PERCENT, DUPLICATE_PERCENT, RANGE_MIN, RANGE_MAX, CUSTOM_COLUMN
    threshold = Column(Float, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="rules")
