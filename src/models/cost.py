import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Float, JSON
from datetime import datetime
from src.database import Base

class CloudCostSnapshot(Base):
    __tablename__ = "cloud_cost_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_spend = Column(Float, nullable=False)
    cost_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class ComputeUsageMetric(Base):
    __tablename__ = "compute_usage_metrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id = Column(String, nullable=False) # e.g. profiling_job_id, workflow_exec_id
    resource_type = Column(String, nullable=False) # profiling, workflow, ai_analysis
    cpu_milliseconds = Column(Float, default=0.0, nullable=False)
    estimated_cost = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class StorageUsageMetric(Base):
    __tablename__ = "storage_usage_metrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    bytes_stored = Column(Float, nullable=False)
    estimated_monthly_cost = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
