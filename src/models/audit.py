import uuid
from sqlalchemy import Column, String, DateTime, Uuid, JSON
from datetime import datetime
from src.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, nullable=True) # Nullable for system-triggered tasks
    action = Column(String, nullable=False) # e.g., dataset_uploaded, version_created, profile_started, etc.
    target_type = Column(String, nullable=False) # e.g., dataset, dataset_version, profiling_job, data_quality_rule
    target_id = Column(Uuid, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
