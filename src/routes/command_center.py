import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.dashboard import ReliabilityDashboardSnapshot
from src.models.observability import DataIncident
from src.models.governance import ComplianceSnapshot
from src.services.command_center_engine import CommandCenterEngine

router = APIRouter(prefix="/api/v1/dashboard", tags=["Reliability Command Center"])


@router.get("/reliability")
def get_reliability_dashboard(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Trigger a new point-in-time calculation snapshot
    snapshot = CommandCenterEngine.generate_snapshot(db)
    return {
        "id": snapshot.id,
        "platform_health_score": snapshot.platform_health_score,
        "datasets_monitored": snapshot.datasets_monitored,
        "active_incidents": snapshot.active_incidents,
        "critical_incidents": snapshot.critical_incidents,
        "sla_compliance_pct": snapshot.sla_compliance_pct,
        "quality_avg": snapshot.quality_avg,
        "drift_avg": snapshot.drift_avg,
        "anomaly_avg": snapshot.anomaly_avg,
        "created_at": snapshot.created_at.isoformat()
    }

@router.get("/incidents")
def get_incidents_summary(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    total_active = db.query(DataIncident).filter(DataIncident.status == "OPEN").count()
    investigating = db.query(DataIncident).filter(DataIncident.status == "INVESTIGATING").count()
    resolved = db.query(DataIncident).filter(DataIncident.status == "RESOLVED").count()
    critical = db.query(DataIncident).filter(
        DataIncident.status == "OPEN",
        DataIncident.severity == "critical"
    ).count()

    return {
        "total_active": total_active,
        "investigating": investigating,
        "resolved": resolved,
        "critical": critical
    }

@router.get("/compliance")
def get_compliance_summary(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    snapshots = db.query(ComplianceSnapshot).all()
    if not snapshots:
        return {"average_compliance_score": 100.0}

    latest_scores = {}
    for s in snapshots:
        if s.dataset_id not in latest_scores or s.created_at > latest_scores[s.dataset_id].created_at:
            latest_scores[s.dataset_id] = s

    avg = sum(s.compliance_score for s in latest_scores.values()) / len(latest_scores)
    return {"average_compliance_score": avg}

@router.get("/history")
def get_dashboard_history(limit: Optional[int] = 30, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    snapshots = db.query(ReliabilityDashboardSnapshot).order_by(
        ReliabilityDashboardSnapshot.created_at.desc()
    ).limit(limit).all()

    return [{
        "id": s.id,
        "platform_health_score": s.platform_health_score,
        "datasets_monitored": s.datasets_monitored,
        "active_incidents": s.active_incidents,
        "critical_incidents": s.critical_incidents,
        "sla_compliance_pct": s.sla_compliance_pct,
        "quality_avg": s.quality_avg,
        "drift_avg": s.drift_avg,
        "anomaly_avg": s.anomaly_avg,
        "created_at": s.created_at.isoformat()
    } for s in snapshots]
