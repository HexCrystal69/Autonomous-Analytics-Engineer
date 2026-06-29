import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from datetime import datetime
from src.database import Base

class DatasetCertification(Base):
    __tablename__ = "dataset_certifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    certification_level = Column(String, nullable=False) # bronze, silver, gold, platinum
    approved_by = Column(String, nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
