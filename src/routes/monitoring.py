import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.monitoring import MonitoringRule, MonitoringAlert
from src.services.monitoring_engine import MonitoringEngine

router = APIRouter(prefix="/api/v1/monitoring", tags=["DataOps Monitoring"])


class MonitoringRuleCreateSchema(BaseModel):
    dataset_id: uuid.UUID
    metric: str
    threshold: float
    comparison_operator: str
    severity: Optional[str] = "medium"

@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_monitoring_rule(payload: MonitoringRuleCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rule = MonitoringEngine.create_rule(
        db,
        payload.dataset_id,
        payload.metric,
        payload.threshold,
        payload.comparison_operator,
        payload.severity
    )
    return {
        "id": rule.id,
        "dataset_id": rule.dataset_id,
        "metric": rule.metric,
        "threshold": rule.threshold,
        "comparison_operator": rule.comparison_operator,
        "severity": rule.severity
    }

@router.get("/rules")
def list_monitoring_rules(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rules = db.query(MonitoringRule).all()
    return [{
        "id": r.id,
        "dataset_id": r.dataset_id,
        "metric": r.metric,
        "threshold": r.threshold,
        "comparison_operator": r.comparison_operator,
        "severity": r.severity
    } for r in rules]

@router.get("/alerts")
def list_monitoring_alerts(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    alerts = db.query(MonitoringAlert).all()
    return [{
        "id": a.id,
        "rule_id": a.rule_id,
        "status": a.status,
        "message": a.message,
        "triggered_at": a.triggered_at.isoformat(),
        "acknowledged_by": a.acknowledged_by,
        "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        "resolved_by": a.resolved_by,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "trace_id": a.trace_id,
        "span_id": a.span_id
    } for a in alerts]

@router.post("/alerts/{id}/acknowledge")
def acknowledge_alert(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Extract user email
    user_email = current_user.email if hasattr(current_user, 'email') else "operator@platform.com"
    alert = MonitoringEngine.acknowledge_alert(db, id, user_email)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        "id": alert.id,
        "status": alert.status,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
    }

@router.post("/alerts/{id}/resolve")
def resolve_alert(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Extract user email
    user_email = current_user.email if hasattr(current_user, 'email') else "operator@platform.com"
    alert = MonitoringEngine.resolve_alert(db, id, user_email)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        "id": alert.id,
        "status": alert.status,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
    }
