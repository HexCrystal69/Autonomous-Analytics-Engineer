import uuid
from sqlalchemy import Column, String, DateTime, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="Viewer", nullable=False)  # Admin, Editor, Viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
