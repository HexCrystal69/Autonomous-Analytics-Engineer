import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    summary_metrics = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset_version = relationship("DatasetVersion", back_populates="snapshots")
