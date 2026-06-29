import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class AnomalyDetectionRun(Base):
    __tablename__ = "anomaly_detection_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    algorithm = Column(String, nullable=False) # zscore, iqr, isolation_forest, local_outlier_factor
    status = Column(String, default="pending", nullable=False) # pending, running, completed, failed
    anomalies_found = Column(Integer, default=0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    anomalies = relationship("DetectedAnomaly", back_populates="run", cascade="all, delete-orphan")

class DetectedAnomaly(Base):
    __tablename__ = "detected_anomalies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id = Column(Uuid, ForeignKey("anomaly_detection_runs.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String, nullable=False)
    row_index = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    anomaly_type = Column(String, nullable=False) # e.g. POINT, OUTLIER
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("AnomalyDetectionRun", back_populates="anomalies")
