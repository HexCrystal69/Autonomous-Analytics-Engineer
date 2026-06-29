import uuid
from typing import Optional
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.monitoring_engine import MonitoringEngine

@celery_app.task(name="src.tasks.monitoring_tasks.run_monitoring")
def run_monitoring(dataset_version_uuid: str, trace_id: Optional[str] = None, span_id: Optional[str] = None) -> str:
    db = SessionLocal()
    try:
        ver_id = uuid.UUID(dataset_version_uuid)
        alerts = MonitoringEngine.evaluate_rules(db, ver_id, trace_id, span_id)
        return f"Monitoring completed. Triggered {len(alerts)} alerts."
    except Exception as e:
        return f"Error in monitoring task: {str(e)}"
    finally:
        db.close()
