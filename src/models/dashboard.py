import uuid
from sqlalchemy import Column, String, DateTime, Uuid, Float, Integer
from datetime import datetime
from src.database import Base

class ReliabilityDashboardSnapshot(Base):
    __tablename__ = "reliability_dashboard_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    platform_health_score = Column(Float, nullable=False)
    datasets_monitored = Column(Integer, default=0, nullable=False)
    active_incidents = Column(Integer, default=0, nullable=False)
    critical_incidents = Column(Integer, default=0, nullable=False)
    sla_compliance_pct = Column(Float, default=100.0, nullable=False)
    quality_avg = Column(Float, default=100.0, nullable=False)
    drift_avg = Column(Float, default=0.0, nullable=False)
    anomaly_avg = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
