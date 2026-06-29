import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.drift import DatasetDriftRun, ColumnDriftResult, DriftBaseline
from src.models.reliability import DatasetHealthHistory
from src.routes.auth import get_current_user, require_role
from src.tasks.quality_tasks import run_dataset_drift_detection

router = APIRouter(prefix="/api/v1/datasets", tags=["drift"])

@router.post("/{dataset_id}/baseline", status_code=status.HTTP_200_OK)
def set_drift_baseline(
    dataset_id: uuid.UUID,
    baseline_version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    version = db.query(DatasetVersion).filter(
        DatasetVersion.id == baseline_version_id,
        DatasetVersion.dataset_id == dataset_id
    ).first()
    if not version:
        raise HTTPException(status_code=400, detail="Target baseline version not found in dataset")

    baseline = db.query(DriftBaseline).filter(DriftBaseline.dataset_id == dataset_id).first()
    if baseline:
        baseline.baseline_version_id = baseline_version_id
        baseline.created_at = datetime.utcnow() if 'datetime' in globals() else baseline.created_at
    else:
        baseline = DriftBaseline(dataset_id=dataset_id, baseline_version_id=baseline_version_id)
        db.add(baseline)
    
    db.commit()
    return {"message": "Drift baseline successfully set", "baseline_version_id": baseline_version_id}

@router.post("/{dataset_id}/drift/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_drift_run(
    dataset_id: uuid.UUID,
    target_version_id: uuid.UUID,
    baseline_version_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Determine baseline
    base_id = baseline_version_id
    if not base_id:
        baseline_record = db.query(DriftBaseline).filter(DriftBaseline.dataset_id == dataset_id).first()
        if baseline_record:
            base_id = baseline_record.baseline_version_id
        else:
            # Fallback to earliest version
            earliest_ver = db.query(DatasetVersion)\
                .filter(DatasetVersion.dataset_id == dataset_id)\
                .order_by(DatasetVersion.version_number.asc())\
                .first()
            if earliest_ver:
                base_id = earliest_ver.id

    if not base_id:
        raise HTTPException(status_code=400, detail="No baseline version defined for drift detection")

    # Trigger via Celery task
    run_dataset_drift_detection.delay(str(target_version_id), str(base_id))

    return {
        "status": "pending",
        "message": "Drift analysis task queued",
        "target_version_id": target_version_id,
        "baseline_version_id": base_id
    }

@router.get("/{dataset_id}/drift")
def list_drift_runs(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find all versions of this dataset
    versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).all()
    version_ids = [v.id for v in versions]

    drift_runs = db.query(DatasetDriftRun).filter(
        DatasetDriftRun.dataset_version_id.in_(version_ids)
    ).order_by(DatasetDriftRun.created_at.desc()).all()

    results = []
    for run in drift_runs:
        column_results = db.query(ColumnDriftResult).filter(ColumnDriftResult.drift_run_id == run.id).all()
        results.append({
            "id": run.id,
            "dataset_version_id": run.dataset_version_id,
            "baseline_version_id": run.baseline_version_id,
            "status": run.status,
            "overall_drift_score": run.overall_drift_score,
            "created_at": run.created_at,
            "column_results": column_results
        })
    return results

@router.get("/{dataset_id}/health/history")
def get_health_history(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).all()
    version_ids = [v.id for v in versions]

    history = db.query(DatasetHealthHistory).filter(
        DatasetHealthHistory.dataset_version_id.in_(version_ids)
    ).order_by(DatasetHealthHistory.recorded_at.asc()).all()
    return history
