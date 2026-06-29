import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Boolean, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False) # incident_created, health_drop, drift_detected, sla_breach, contract_failure
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowDependency(Base):
    __tablename__ = "workflow_dependencies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    parent_workflow_id = Column(Uuid, ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False)
    child_workflow_id = Column(Uuid, ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String, default="triggers", nullable=False) # blocks, triggers, requires

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id = Column(Uuid, ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="RUNNING", nullable=False) # RUNNING, SUCCESS, FAILED
    result_json = Column(JSON, nullable=True)
    workflow_validation_status = Column(String, default="VALID", nullable=False) # VALID, CYCLE_DETECTED, INVALID
    validation_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    last_error = Column(String, nullable=True)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("WorkflowDefinition", back_populates="executions")
    audit_logs = relationship("WorkflowAuditLog", back_populates="execution", cascade="all, delete-orphan")

class WorkflowAuditLog(Base):
    __tablename__ = "workflow_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_execution_id = Column(Uuid, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    event_message = Column(String, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    execution = relationship("WorkflowExecution", back_populates="audit_logs")
