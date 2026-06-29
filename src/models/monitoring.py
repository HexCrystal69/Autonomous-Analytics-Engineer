import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class MonitoringRule(Base):
    __tablename__ = "monitoring_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    metric = Column(String, nullable=False) # health_score, quality_score, drift_score, freshness_delay, anomaly_count
    threshold = Column(Float, nullable=False)
    comparison_operator = Column(String, nullable=False) # >, <, >=, <=, ==
    severity = Column(String, default="medium", nullable=False) # low, medium, high, critical

    alerts = relationship("MonitoringAlert", back_populates="rule", cascade="all, delete-orphan")

class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_id = Column(Uuid, ForeignKey("monitoring_rules.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="OPEN", nullable=False) # OPEN, ACKNOWLEDGED, RESOLVED, SUPPRESSED
    message = Column(String, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # lifecycle tracking
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # OTel integration
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)

    rule = relationship("MonitoringRule", back_populates="alerts")
