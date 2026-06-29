import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DatasetDriftRun(Base):
    __tablename__ = "dataset_drift_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    baseline_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="pending", nullable=False) # pending, running, completed, failed
    overall_drift_score = Column(Float, default=0.0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    results = relationship("ColumnDriftResult", back_populates="drift_run", cascade="all, delete-orphan")

class ColumnDriftResult(Base):
    __tablename__ = "column_drift_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    drift_run_id = Column(Uuid, ForeignKey("dataset_drift_runs.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String, nullable=False)
    drift_metric = Column(String, nullable=False) # PSI, MEAN_SHIFT, STD_SHIFT, DIST_DRIFT, CARD_DRIFT
    drift_score = Column(Float, nullable=False)
    severity = Column(String, nullable=False) # LOW, MEDIUM, HIGH

    drift_run = relationship("DatasetDriftRun", back_populates="results")

class DriftBaseline(Base):
    __tablename__ = "drift_baselines"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), unique=True, nullable=False)
    baseline_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
