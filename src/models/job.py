import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class ProfilingJob(Base):
    __tablename__ = "profiling_jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, PROCESSING, SUCCESS, FAILED
    task_id = Column(String, nullable=True)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    dataset_version = relationship("DatasetVersion", back_populates="jobs")
