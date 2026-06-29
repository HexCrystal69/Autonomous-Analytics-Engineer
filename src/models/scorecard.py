import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Uuid, JSON
from datetime import datetime
from src.database import Base

class ReliabilityScorecard(Base):
    __tablename__ = "reliability_scorecards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    health_score = Column(Float, nullable=False)
    quality_score = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    drift_score = Column(Float, nullable=False)
    reliability_score = Column(Float, nullable=False)
    classification = Column(String, nullable=False) # excellent, good, warning, critical
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class ExecutiveScorecard(Base):
    __tablename__ = "executive_scorecards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    overall_platform_score = Column(Float, nullable=False)
    datasets_monitored = Column(Integer, nullable=False)
    critical_incidents = Column(Integer, nullable=False)
    sla_compliance = Column(Float, nullable=False)
    top_risks = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
