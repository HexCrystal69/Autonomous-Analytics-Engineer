import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.impact import ImpactAnalysis
from src.services.impact_engine import ImpactEngine

router = APIRouter(prefix="/api/v1/impact", tags=["Impact Analysis"])


@router.post("/{dataset_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_impact_analysis(dataset_id: uuid.UUID, change_type: Optional[str] = "schema_change", db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Trigger impact analysis
    res = ImpactEngine.analyze_impact(db, dataset_id, change_type)
    return {
        "id": res.id,
        "dataset_id": res.dataset_id,
        "change_type": res.change_type,
        "affected_datasets": json.loads(res.affected_datasets),
        "affected_reports": res.affected_reports,
        "risk_score": res.risk_score,
        "created_at": res.created_at.isoformat()
    }

@router.get("/{dataset_id}")
def get_impact_analysis(dataset_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    res = db.query(ImpactAnalysis).filter(
        ImpactAnalysis.dataset_id == dataset_id
    ).order_by(ImpactAnalysis.created_at.desc()).first()

    if not res:
        raise HTTPException(status_code=404, detail="No impact analysis records found for this dataset")

    return {
        "id": res.id,
        "dataset_id": res.dataset_id,
        "change_type": res.change_type,
        "affected_datasets": json.loads(res.affected_datasets),
        "affected_reports": res.affected_reports,
        "risk_score": res.risk_score,
        "created_at": res.created_at.isoformat()
    }
