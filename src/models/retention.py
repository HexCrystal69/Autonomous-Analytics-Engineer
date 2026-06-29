import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Integer
from datetime import datetime
from src.database import Base

class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    retention_days = Column(Integer, default=30, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DataPurgeExecution(Base):
    __tablename__ = "data_purge_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    purged_records_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default="SUCCESS", nullable=False) # SUCCESS, FAILED
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
