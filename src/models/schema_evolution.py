import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class SchemaVersion(Base):
    __tablename__ = "schema_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    schema_hash = Column(String, nullable=False)
    columns_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    changes = relationship("SchemaChange", back_populates="schema_version", cascade="all, delete-orphan")

class SchemaChange(Base):
    __tablename__ = "schema_changes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    schema_version_id = Column(Uuid, ForeignKey("schema_versions.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String, nullable=False)
    change_type = Column(String, nullable=False) # ADDED, REMOVED, TYPE_CHANGE, NULLABLE_CHANGE
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    is_breaking = Column(Boolean, default=False, nullable=False)

    schema_version = relationship("SchemaVersion", back_populates="changes")
