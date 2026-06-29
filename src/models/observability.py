import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class DataIncident(Base):
    __tablename__ = "data_incidents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_version_id = Column(Uuid, ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="OPEN", nullable=False) # OPEN, INVESTIGATING, RESOLVED
    severity = Column(String, default="medium", nullable=False) # low, medium, high, critical
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # OTel integration
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)

    comments = relationship("IncidentComment", back_populates="incident", cascade="all, delete-orphan")
    assignments = relationship("IncidentAssignment", back_populates="incident", cascade="all, delete-orphan")


class IncidentComment(Base):
    __tablename__ = "incident_comments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id = Column(Uuid, ForeignKey("data_incidents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Uuid, nullable=True) # System comments can have null user
    comment = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    incident = relationship("DataIncident", back_populates="comments")

class IncidentAssignment(Base):
    __tablename__ = "incident_assignments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id = Column(Uuid, ForeignKey("data_incidents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    incident = relationship("DataIncident", back_populates="assignments")
