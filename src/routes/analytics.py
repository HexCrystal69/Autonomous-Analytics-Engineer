import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import get_db
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.reliability import ValidationReport, DatasetHealthHistory
from src.routes.auth import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/quality-summary")
def get_quality_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_execs = db.query(DataQualityExecution).count()
    completed_execs = db.query(DataQualityExecution).filter(DataQualityExecution.status == "completed").count()
    failed_execs = db.query(DataQualityExecution).filter(DataQualityExecution.status == "failed").count()
    total_violations = db.query(QualityViolation).count()

    return {
        "total_executions": total_execs,
        "completed_executions": completed_execs,
        "failed_executions": failed_execs,
        "total_violations": total_violations
    }

@router.get("/anomaly-summary")
def get_anomaly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_runs = db.query(AnomalyDetectionRun).count()
    total_anomalies = db.query(DetectedAnomaly).count()
    
    # Group by type
    type_counts = db.query(
        DetectedAnomaly.anomaly_type, func.count(DetectedAnomaly.id)
    ).group_by(DetectedAnomaly.anomaly_type).all()

    return {
        "total_runs": total_runs,
        "total_anomalies_detected": total_anomalies,
        "anomaly_types_distribution": {t: c for t, c in type_counts}
    }

@router.get("/top-violations")
def get_top_violations(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Group by column name to find the most violating columns
    violations = db.query(
        QualityViolation.column_name, func.count(QualityViolation.id).label("count")
    ).group_by(QualityViolation.column_name).order_by(func.count(QualityViolation.id).desc()).limit(limit).all()

    return [
        {"column_name": col or "OVERALL", "violation_count": count}
        for col, count in violations
    ]

@router.get("/data-health-score")
def get_average_data_health_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    avg_score = db.query(func.avg(ValidationReport.health_score)).scalar()
    avg_quality = db.query(func.avg(ValidationReport.quality_score)).scalar()
    avg_anomaly = db.query(func.avg(ValidationReport.anomaly_score)).scalar()
    avg_drift = db.query(func.avg(ValidationReport.drift_score)).scalar()

    return {
        "average_health_score": round(float(avg_score), 2) if avg_score is not None else 100.0,
        "average_quality_score": round(float(avg_quality), 2) if avg_quality is not None else 100.0,
        "average_anomaly_score": round(float(avg_anomaly), 2) if avg_anomaly is not None else 100.0,
        "average_drift_score": round(float(avg_drift), 2) if avg_drift is not None else 100.0
    }

@router.get("/datasets/{dataset_id}/history")
def get_dataset_validation_history(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).all()
    version_ids = [v.id for v in versions]

    reports = db.query(ValidationReport).filter(
        ValidationReport.dataset_version_id.in_(version_ids)
    ).order_by(ValidationReport.created_at.asc()).all()

    return [
        {
            "id": r.id,
            "dataset_version_id": r.dataset_version_id,
            "health_score": r.health_score,
            "quality_score": r.quality_score,
            "anomaly_score": r.anomaly_score,
            "drift_score": r.drift_score,
            "summary": r.report_json,
            "created_at": r.created_at
        }
        for r in reports
    ]
