import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Uuid, JSON
from datetime import datetime
from src.database import Base

class RuleTemplate(Base):
    __tablename__ = "rule_templates"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False) # e.g. "Email Validation", "Null Threshold"
    category = Column(String, nullable=False) # e.g. "Validation", "Format"
    description = Column(String, nullable=False)
    default_threshold = Column(Float, nullable=False)

class ValidationReport(Base):
    __tablename__ = "validation_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    quality_execution_id = Column(Uuid, ForeignKey("data_quality_executions.id", ondelete="SET NULL"), nullable=True)
    anomaly_run_id = Column(Uuid, ForeignKey("anomaly_detection_runs.id", ondelete="SET NULL"), nullable=True)
    health_score = Column(Float, nullable=False)
    quality_score = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    drift_score = Column(Float, nullable=False)
    report_json = Column(JSON, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DatasetHealthHistory(Base):
    __tablename__ = "dataset_health_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    health_score = Column(Float, nullable=False)
    quality_score = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
