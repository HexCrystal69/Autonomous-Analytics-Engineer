import uuid
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from src.models.audit import AuditLog

def log_audit(
    db: Session,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    metadata_json: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Helper function to create an AuditLog entry."""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata_json
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
