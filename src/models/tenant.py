import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    members = relationship("TenantMember", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSettings", uselist=False, back_populates="tenant", cascade="all, delete-orphan")

class TenantMember(Base):
    __tablename__ = "tenant_members"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default="Viewer", nullable=False) # Admin, Editor, Viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="members")

class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    settings_json = Column(JSON, default=dict, nullable=False) # e.g. quotas, custom themes

    tenant = relationship("Tenant", back_populates="settings")
