import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from datetime import datetime
from src.database import Base

class DatasetDependency(Base):
    __tablename__ = "dataset_dependencies"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    source_dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    target_dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String, default="derived_from", nullable=False) # derived_from, joined_with, aggregated_from, filtered_from
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
