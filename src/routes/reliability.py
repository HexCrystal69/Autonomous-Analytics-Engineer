import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.scorecard import ReliabilityScorecard
from src.routes.auth import get_current_user

router = APIRouter(prefix="/api/v1/reliability", tags=["reliability"])

@router.get("/history")
def get_scorecard_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scs = db.query(ReliabilityScorecard).order_by(ReliabilityScorecard.created_at.desc()).all()
    return scs

@router.get("/{dataset_version_id}")
def get_scorecard(
    dataset_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sc = db.query(ReliabilityScorecard).filter(
        ReliabilityScorecard.dataset_version_id == dataset_version_id
    ).first()
    if not sc:
        raise HTTPException(status_code=404, detail="Scorecard not found for dataset version")
    return sc
