import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.dataset import DatasetVersion
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.routes.auth import get_current_user, require_role
from src.tasks.quality_tasks import run_anomaly_detection

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])

@router.post("/versions/{version_id}/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_anomaly_run(
    version_id: uuid.UUID,
    algorithm: str = "iqr", # zscore, iqr, isolation_forest, local_outlier_factor
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    run = AnomalyDetectionRun(
        dataset_version_id=version_id,
        algorithm=algorithm,
        status="pending"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_anomaly_detection.delay(str(version_id), algorithm)

    return {
        "run_id": run.id,
        "status": run.status,
        "algorithm": run.algorithm,
        "message": "Anomaly detection task triggered"
    }

@router.get("/versions/{version_id}")
def get_anomaly_runs(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    runs = db.query(AnomalyDetectionRun).filter(
        AnomalyDetectionRun.dataset_version_id == version_id
    ).order_by(AnomalyDetectionRun.started_at.desc()).all()
    return runs

@router.get("/{run_id}")
def get_anomaly_run_details(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = db.query(AnomalyDetectionRun).filter(AnomalyDetectionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Anomaly run not found")
    
    anomalies = db.query(DetectedAnomaly).filter(DetectedAnomaly.run_id == run_id).all()
    return {
        "id": run.id,
        "dataset_version_id": run.dataset_version_id,
        "algorithm": run.algorithm,
        "status": run.status,
        "anomalies_found": run.anomalies_found,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "anomalies": anomalies
    }
