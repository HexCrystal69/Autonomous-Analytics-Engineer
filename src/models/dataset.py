import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    owner_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    rules = relationship("DataQualityRule", back_populates="dataset", cascade="all, delete-orphan")
    tags = relationship("DatasetTag", back_populates="dataset", cascade="all, delete-orphan")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="versions")
    profile = relationship("DatasetProfile", back_populates="dataset_version", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("ProfilingJob", back_populates="dataset_version", cascade="all, delete-orphan")
    snapshots = relationship("ProfileSnapshot", back_populates="dataset_version", cascade="all, delete-orphan")

class DatasetTag(Base):
    __tablename__ = "dataset_tags"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="tags")
