import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Uuid, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="OPEN", nullable=False) # OPEN, IN_PROGRESS, MITIGATED, RESOLVED, CLOSED
    priority = Column(String, default="medium", nullable=False) # low, medium, high, critical
    resolution_notes = Column(String, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    findings = relationship("InvestigationFinding", back_populates="investigation", cascade="all, delete-orphan")
    sla = relationship("InvestigationSLA", uselist=False, back_populates="investigation", cascade="all, delete-orphan")

class InvestigationFinding(Base):
    __tablename__ = "investigation_findings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id = Column(Uuid, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    finding_type = Column(String, nullable=False)
    evidence_json = Column(JSON, nullable=False)
    source_table = Column(String, nullable=True) # quality_violation, detected_anomaly, dataset_drift_run, data_incident
    source_record_id = Column(Uuid, nullable=True)
    confidence = Column(Float, default=100.0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    investigation = relationship("Investigation", back_populates="findings")

class InvestigationSLA(Base):
    __tablename__ = "investigation_slas"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id = Column(Uuid, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    target_resolution_hours = Column(Integer, default=24, nullable=False)
    actual_resolution_hours = Column(Integer, nullable=True)
    breached = Column(Boolean, default=False, nullable=False)

    investigation = relationship("Investigation", back_populates="sla")
