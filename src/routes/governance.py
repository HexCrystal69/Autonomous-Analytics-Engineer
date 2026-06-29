import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.governance import GovernancePolicy, ComplianceSnapshot, DatasetPolicyMapping
from src.services.governance_engine import GovernanceEngine

router = APIRouter(prefix="/api/v1/governance", tags=["Governance Layer"])


class PolicyCreateSchema(BaseModel):
    name: str
    category: str # PII Compliance, Retention Policy, Freshness Policy, Schema Governance, Quality Standards
    description: Optional[str] = None
    severity: Optional[str] = "medium"

@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    p = GovernanceEngine.create_policy(
        db,
        payload.name,
        payload.category,
        payload.description,
        payload.severity
    )
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "severity": p.severity
    }

@router.get("/policies")
def list_policies(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    policies = db.query(GovernancePolicy).all()
    return [{
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "severity": p.severity
    } for p in policies]

@router.get("/compliance")
def get_overall_compliance(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    snapshots = db.query(ComplianceSnapshot).all()
    if not snapshots:
        return {"average_compliance_score": 100.0}

    # Group by dataset_id to get the latest compliance score
    latest_scores = {}
    for s in snapshots:
        if s.dataset_id not in latest_scores or s.created_at > latest_scores[s.dataset_id].created_at:
            latest_scores[s.dataset_id] = s

    avg = sum(s.compliance_score for s in latest_scores.values()) / len(latest_scores)
    return {"average_compliance_score": avg}

@router.get("/compliance/{dataset_id}")
def get_dataset_compliance(dataset_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Trigger fresh compliance evaluation before retrieving
    snapshot = GovernanceEngine.evaluate_compliance(db, dataset_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No compliance history found")

    return {
        "id": snapshot.id,
        "dataset_id": snapshot.dataset_id,
        "compliance_score": snapshot.compliance_score,
        "failed_policies": snapshot.failed_policies,
        "passed_policies": snapshot.passed_policies,
        "created_at": snapshot.created_at.isoformat()
    }
