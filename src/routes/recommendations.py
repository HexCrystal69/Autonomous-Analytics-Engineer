import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.recommendation import Recommendation, RecommendationOutcome
from src.services.copilot_engine import CopilotEngine

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations Workspace"])

@router.get("")
def list_recommendations(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    recs = db.query(Recommendation).all()
    return [{"id": r.id, "title": r.title, "priority": r.priority, "status": r.status} for r in recs]

@router.get("/outcomes")
def list_outcomes(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    outcomes = db.query(RecommendationOutcome).all()
    return [{"id": o.id, "recommendation_id": o.recommendation_id, "roi_score": o.roi_score} for o in outcomes]

@router.get("/{id}")
def get_recommendation(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rec = db.query(Recommendation).filter(Recommendation.id == id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {
        "id": rec.id,
        "title": rec.title,
        "description": rec.description,
        "priority": rec.priority,
        "status": rec.status,
        "cost_factor": rec.implementation_cost_factor,
        "outcome": {
            "roi_score": rec.outcome.roi_score,
            "improvement_pct": rec.outcome.improvement_pct
        } if rec.outcome else None
    }

@router.patch("/{id}")
def patch_recommendation(
    id: uuid.UUID,
    status: str,
    cost_factor: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    rec = db.query(Recommendation).filter(Recommendation.id == id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    status_upper = status.upper()
    rec.status = status_upper
    if cost_factor is not None:
        rec.implementation_cost_factor = cost_factor

    if status_upper in ["IMPLEMENTED", "APPLIED"]:
        rec.implemented_at = datetime.utcnow()
        rec.implemented_by = current_user.email
        # Seed an outcome automatically for testing
        CopilotEngine.log_recommendation_outcome(db, id, 80.0, 95.0)


    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "status": rec.status}

from datetime import datetime
