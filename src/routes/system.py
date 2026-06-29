import shutil
import os
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import get_db
from src.config import settings
from src.celery_app import celery_app
from src.models.quality_execution import DataQualityExecution
from src.models.anomaly_run import AnomalyDetectionRun
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import redis

router = APIRouter(tags=["system"])

# Prometheus Metrics definition
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"])

# Milestone 2 Observability Metrics
QUALITY_RUNS = Counter("quality_runs_total", "Total quality runs executed")
QUALITY_FAILURES = Counter("quality_failures_total", "Total failed quality runs")
VIOLATIONS = Counter("violations_total", "Total data quality violations found")
ANOMALY_RUNS = Counter("anomaly_runs_total", "Total anomaly detection runs executed")
ANOMALIES_DETECTED = Counter("anomalies_detected_total", "Total anomalies detected")
HEALTH_CALCS = Counter("health_score_calculations_total", "Total health score calculation runs")
PIPELINE_DURATION = Histogram("pipeline_duration_seconds", "Total duration of health pipelines")

# Milestone 3 Observability Metrics
COMPARISONS_RUN = Counter("dataset_comparisons_total", "Total dataset comparisons executed")
RCA_RUNS = Counter("root_cause_runs_total", "Total root cause analysis runs executed")
RECS_GENERATED = Counter("recommendations_generated_total", "Total recommendations generated")
SCORECARDS_GENERATED = Counter("scorecards_generated_total", "Total reliability scorecards generated")
LEADERBOARD_UPDATES = Counter("leaderboard_updates_total", "Total leaderboard rank updates executed")
ANALYTICS_PIPELINE_DURATION = Histogram("analytics_pipeline_duration_seconds", "Total duration of executive analytics pipelines")


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "database": "unhealthy",
        "redis": "unhealthy",
        "celery": "unhealthy",
        "storage": "unhealthy",
        "disk_usage": {},
        "queue_depth": 0,
        "latest_quality_run_status": None,
        "latest_anomaly_run_status": None
    }
    
    # 1. Database Check
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
        
        # Latest runs check
        latest_quality = db.query(DataQualityExecution).order_by(DataQualityExecution.started_at.desc()).first()
        if latest_quality:
            health_status["latest_quality_run_status"] = latest_quality.status

        latest_anomaly = db.query(AnomalyDetectionRun).order_by(AnomalyDetectionRun.started_at.desc()).first()
        if latest_anomaly:
            health_status["latest_anomaly_run_status"] = latest_anomaly.status
    except Exception:
        pass

    # 2. Redis & Queue Depth Check
    r_client = None
    try:
        r_client = redis.from_url(settings.REDIS_URL)
        if r_client.ping():
            health_status["redis"] = "healthy"
            health_status["queue_depth"] = r_client.llen("celery") or 0
    except Exception:
        pass

    # 3. Celery Check
    try:
        if r_client:
            insp = celery_app.control.inspect(timeout=0.5)
            stats = insp.stats()
            if stats:
                health_status["celery"] = "healthy"
            else:
                health_status["celery"] = "healthy" if health_status["redis"] == "healthy" else "unhealthy"
        else:
            health_status["celery"] = "unhealthy"
    except Exception:
        health_status["celery"] = "healthy" if health_status["redis"] == "healthy" else "unhealthy"

    # 4. Storage & Disk Check
    try:
        if settings.STORAGE_PROVIDER == "local":
            storage_path = settings.STORAGE_DIR
            temp_file = os.path.join(storage_path, ".health_check_temp")
            with open(temp_file, "w") as f:
                f.write("health_check")
            os.remove(temp_file)
            health_status["storage"] = "healthy"

            # Disk Usage
            total, used, free = shutil.disk_usage(storage_path)
            health_status["disk_usage"] = {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 2)
            }
    except Exception:
        pass

    return health_status

@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
