import uuid
from sqlalchemy import Column, String, DateTime, Uuid
from datetime import datetime
from src.database import Base

class SecurityAuditEvent(Base):
    __tablename__ = "security_audit_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False) # e.g. login_failure, rbac_violation, rate_limit_breach
    user_email = Column(String, nullable=True)
    details = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
