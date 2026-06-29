import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.root_cause import RootCauseAnalysis
from src.models.dataset import DatasetVersion
from src.routes.auth import get_current_user, require_role
from src.tasks.analytics_tasks import run_root_cause_analysis

router = APIRouter(prefix="/api/v1/root-cause", tags=["root-cause"])

@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_rca(
    dataset_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    run_root_cause_analysis.delay(str(dataset_version_id))

    return {
        "status": "pending",
        "message": "Root Cause Analysis task triggered",
        "dataset_version_id": dataset_version_id
    }

@router.get("/{id}")
def get_rca(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rca = db.query(RootCauseAnalysis).filter(RootCauseAnalysis.id == id).first()
    if not rca:
        raise HTTPException(status_code=404, detail="RCA record not found")
    return rca

@router.get("")
def list_rcas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rcas = db.query(RootCauseAnalysis).order_by(RootCauseAnalysis.created_at.desc()).all()
    return rcas
