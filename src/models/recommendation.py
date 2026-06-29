import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Float, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    recommendation_type = Column(String, nullable=False) # e.g. NULL_REDUCTION, OUTLIER_INVESTIGATION, RULE_CREATION
    priority = Column(String, default="low", nullable=False) # low, medium, high, critical
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="NEW", nullable=False) # NEW, IN_PROGRESS, IMPLEMENTED, REJECTED, EXPIRED
    implementation_cost_factor = Column(Integer, default=1, nullable=False) # 1=LOW, 2=MEDIUM, 3=HIGH
    implemented_at = Column(DateTime, nullable=True)
    implemented_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    evidence = relationship("RecommendationEvidence", back_populates="recommendation", cascade="all, delete-orphan")
    outcome = relationship("RecommendationOutcome", uselist=False, back_populates="recommendation", cascade="all, delete-orphan")

class RecommendationEvidence(Base):
    __tablename__ = "recommendation_evidences"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_id = Column(Uuid, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    violation_id = Column(Uuid, nullable=True) # ForeignKey to quality_violations, handled loosely to prevent cyclic deletes
    anomaly_id = Column(Uuid, nullable=True) # ForeignKey to anomaly_runs
    incident_id = Column(Uuid, nullable=True) # ForeignKey to data_incidents
    weight = Column(Float, default=1.0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recommendation = relationship("Recommendation", back_populates="evidence")

class RecommendationOutcome(Base):
    __tablename__ = "recommendation_outcomes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_id = Column(Uuid, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    before_score = Column(Float, default=100.0, nullable=False)
    after_score = Column(Float, default=100.0, nullable=False)
    improvement_pct = Column(Float, default=0.0, nullable=False)
    roi_score = Column(Float, default=0.0, nullable=False)
    measured_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recommendation = relationship("Recommendation", back_populates="outcome")
