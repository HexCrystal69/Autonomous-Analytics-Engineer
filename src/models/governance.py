import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False) # PII Compliance, Retention Policy, Freshness Policy, Schema Governance, Quality Standards
    description = Column(String, nullable=True)
    severity = Column(String, default="medium", nullable=False) # low, medium, high, critical

    mappings = relationship("DatasetPolicyMapping", back_populates="policy", cascade="all, delete-orphan")

class DatasetPolicyMapping(Base):
    __tablename__ = "dataset_policy_mappings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    policy_id = Column(Uuid, ForeignKey("governance_policies.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="active", nullable=False) # active, disabled

    policy = relationship("GovernancePolicy", back_populates="mappings")

class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    compliance_score = Column(Float, nullable=False)
    failed_policies = Column(JSON, nullable=False) # list of policy IDs
    passed_policies = Column(JSON, nullable=False) # list of policy IDs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
