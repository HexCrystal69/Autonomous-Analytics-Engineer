import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    rollout_percentage = Column(Integer, default=100, nullable=False) # 0 to 100
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    audits = relationship("FeatureFlagAudit", back_populates="feature_flag", cascade="all, delete-orphan")

class FeatureFlagAudit(Base):
    __tablename__ = "feature_flag_audits"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    feature_flag_id = Column(Uuid, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False) # ENABLED, DISABLED, ROLLOUT_CHANGE
    changed_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    feature_flag = relationship("FeatureFlag", back_populates="audits")
