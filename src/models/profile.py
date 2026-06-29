import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary_metrics = Column(JSON, nullable=False)  # Row/Col count, duplicates, overall missing
    columns_metadata = Column(JSON, nullable=False) # Detailed stat block per column
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset_version = relationship("DatasetVersion", back_populates="profile")
