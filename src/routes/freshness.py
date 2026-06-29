import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.freshness import DatasetFreshnessRecord
from src.routes.auth import get_current_user, require_role
from src.services.freshness_engine import FreshnessEngine

router = APIRouter(prefix="/api/v1/freshness", tags=["freshness"])

@router.post("/log", status_code=status.HTTP_201_CREATED)
def log_freshness_check(
    dataset_id: uuid.UUID,
    expected_refresh_time: datetime,
    actual_refresh_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    record = FreshnessEngine.log_freshness(db, dataset_id, expected_refresh_time, actual_refresh_time)
    return record

@router.get("")
def list_freshness_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    records = db.query(DatasetFreshnessRecord).order_by(DatasetFreshnessRecord.recorded_at.desc()).all()
    return records

@router.get("/{dataset_id}")
def get_dataset_freshness(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    metrics = FreshnessEngine.get_metrics(db, dataset_id)
    history = db.query(DatasetFreshnessRecord).filter(
        DatasetFreshnessRecord.dataset_id == dataset_id
    ).order_by(DatasetFreshnessRecord.recorded_at.desc()).all()

    return {
        "dataset_id": dataset_id,
        "metrics": metrics,
        "freshness_history": history
    }
