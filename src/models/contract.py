import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DataContract(Base):
    __tablename__ = "data_contracts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    description = Column(String, nullable=True)
    contract_version = Column(String, default="1.0.0", nullable=False)
    status = Column(String, default="draft", nullable=False) # draft, active, deprecated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rules = relationship("DataContractRule", back_populates="contract", cascade="all, delete-orphan")
    versions = relationship("ContractVersion", back_populates="contract", cascade="all, delete-orphan")

class DataContractRule(Base):
    __tablename__ = "data_contract_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    contract_id = Column(Uuid, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String, nullable=False) # column_exists, column_type, max_null_pct, uniqueness, freshness, regex, range
    column_name = Column(String, nullable=True)
    expected_value = Column(String, nullable=True)
    severity = Column(String, default="high", nullable=False) # low, medium, high, critical

    contract = relationship("DataContract", back_populates="rules")
    violations = relationship("ContractViolation", back_populates="rule", cascade="all, delete-orphan")

class ContractVersion(Base):
    __tablename__ = "contract_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    contract_id = Column(Uuid, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False)
    version = Column(String, nullable=False)
    schema_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    contract = relationship("DataContract", back_populates="versions")

class ContractViolation(Base):
    __tablename__ = "contract_violations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    contract_rule_id = Column(Uuid, ForeignKey("data_contract_rules.id", ondelete="CASCADE"), nullable=False)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rule = relationship("DataContractRule", back_populates="violations")
