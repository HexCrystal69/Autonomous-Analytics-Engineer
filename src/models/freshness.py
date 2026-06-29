import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Uuid
from datetime import datetime
from src.database import Base

class DatasetFreshnessRecord(Base):
    __tablename__ = "dataset_freshness_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    expected_refresh_time = Column(DateTime, nullable=False)
    actual_refresh_time = Column(DateTime, nullable=True)
    delay_minutes = Column(Integer, default=0, nullable=False)
    status = Column(String, default="on_time", nullable=False) # on_time, late, critical
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
