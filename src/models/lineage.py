import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DatasetLineage(Base):
    __tablename__ = "dataset_lineage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    parent_dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    child_dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    transformation_type = Column(String, nullable=False) # e.g. UPLOAD, FILTER, JOIN, AGGREGATION
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    parent_version = relationship("DatasetVersion", foreign_keys=[parent_dataset_version_id])
    child_version = relationship("DatasetVersion", foreign_keys=[child_dataset_version_id])
