import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.comparison import DatasetComparison, ColumnComparison
from src.models.dataset import DatasetVersion
from src.routes.auth import get_current_user, require_role
from src.tasks.analytics_tasks import run_dataset_comparison

router = APIRouter(prefix="/api/v1/comparisons", tags=["comparisons"])

@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_comparison(
    source_version_id: uuid.UUID,
    target_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    source = db.query(DatasetVersion).filter(DatasetVersion.id == source_version_id).first()
    target = db.query(DatasetVersion).filter(DatasetVersion.id == target_version_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target dataset version not found")

    run_dataset_comparison.delay(str(source_version_id), str(target_version_id))

    return {
        "status": "pending",
        "message": "Dataset comparison task triggered",
        "source_version_id": source_version_id,
        "target_version_id": target_version_id
    }

@router.get("/{id}")
def get_comparison(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comp = db.query(DatasetComparison).filter(DatasetComparison.id == id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison record not found")

    cols = db.query(ColumnComparison).filter(ColumnComparison.comparison_id == id).all()

    return {
        "id": comp.id,
        "source_version_id": comp.source_version_id,
        "target_version_id": comp.target_version_id,
        "row_delta": comp.row_delta,
        "column_delta": comp.column_delta,
        "health_delta": comp.health_delta,
        "quality_delta": comp.quality_delta,
        "anomaly_delta": comp.anomaly_delta,
        "drift_delta": comp.drift_delta,
        "created_at": comp.created_at,
        "column_comparisons": cols
    }

@router.get("")
def list_comparisons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comps = db.query(DatasetComparison).order_by(DatasetComparison.created_at.desc()).all()
    return comps
