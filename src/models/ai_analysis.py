import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Uuid, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    template_text = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    analysis_type = Column(String, nullable=False) # incident_summary, quality_summary, drift_summary, etc.
    status = Column(String, default="COMPLETED", nullable=False) # COMPLETED, REVIEW_REQUIRED, FAILED
    prompt_used = Column(String, nullable=True)
    response_text = Column(String, nullable=True)
    confidence_score = Column(Float, default=100.0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    evidence = relationship("AnalysisEvidence", back_populates="analysis", cascade="all, delete-orphan")
    snapshots = relationship("AnalysisSnapshot", back_populates="analysis", cascade="all, delete-orphan")
    validation = relationship("AnalysisValidation", uselist=False, back_populates="analysis", cascade="all, delete-orphan")

class PromptExecution(Base):
    __tablename__ = "prompt_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    prompt_template_id = Column(Uuid, ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(Uuid, ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False)
    input_hash = Column(String, nullable=False)
    output_hash = Column(String, nullable=False)
    execution_time_ms = Column(Integer, default=0, nullable=False)
    token_estimate = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AnalysisEvidence(Base):
    __tablename__ = "analysis_evidences"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id = Column(Uuid, ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String, nullable=False) # violation, anomaly, drift, incident, scorecard, sla, contract
    evidence_id = Column(Uuid, nullable=False)
    evidence_summary = Column(String, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("AIAnalysis", back_populates="evidence")

class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id = Column(Uuid, ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False)
    prompt_template_id = Column(Uuid, ForeignKey("prompt_templates.id", ondelete="CASCADE"), nullable=False)
    response_text = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    snapshot_version = Column(Integer, default=1, nullable=False)
    parent_snapshot_id = Column(Uuid, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("AIAnalysis", back_populates="snapshots")

class AnalysisValidation(Base):
    __tablename__ = "analysis_validations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id = Column(Uuid, ForeignKey("ai_analyses.id", ondelete="CASCADE"), nullable=False)
    supported_claims = Column(Integer, default=0, nullable=False)
    unsupported_claims = Column(Integer, default=0, nullable=False)
    validation_score = Column(Float, default=100.0, nullable=False)
    validation_status = Column(String, default="SUPPORTED", nullable=False) # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("AIAnalysis", back_populates="validation")
