import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DataQualityExecution(Base):
    __tablename__ = "data_quality_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending", nullable=False) # pending, running, completed, failed
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    summary_json = Column(JSON, nullable=True)

    violations = relationship("QualityViolation", back_populates="execution", cascade="all, delete-orphan")

class QualityViolation(Base):
    __tablename__ = "quality_violations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    execution_id = Column(Uuid, ForeignKey("data_quality_executions.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Uuid, nullable=True)
    severity = Column(String, default="low", nullable=False) # low, medium, high, critical
    column_name = Column(String, nullable=True)
    actual_value = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("DataQualityExecution", back_populates="violations")
