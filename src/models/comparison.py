import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Float, Integer, String, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DatasetComparison(Base):
    __tablename__ = "dataset_comparisons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    source_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    target_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    row_delta = Column(Integer, nullable=False)
    column_delta = Column(Integer, nullable=False)
    health_delta = Column(Float, nullable=False)
    quality_delta = Column(Float, nullable=False)
    anomaly_delta = Column(Float, nullable=False)
    drift_delta = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    columns = relationship("ColumnComparison", back_populates="comparison", cascade="all, delete-orphan")

class ColumnComparison(Base):
    __tablename__ = "column_comparisons"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    comparison_id = Column(Uuid, ForeignKey("dataset_comparisons.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String, nullable=False)
    null_delta = Column(Float, nullable=False)
    mean_delta = Column(Float, nullable=False)
    median_delta = Column(Float, nullable=False)
    std_delta = Column(Float, nullable=False)
    cardinality_delta = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    comparison = relationship("DatasetComparison", back_populates="columns")
