import uuid
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.remediation_engine import RemediationEngine
from src.services.command_center_engine import CommandCenterEngine

@celery_app.task(name="src.tasks.impact_tasks.execute_remediation")
def execute_remediation(incident_uuid: str, action_type: str) -> str:
    db = SessionLocal()
    try:
        inc_id = uuid.UUID(incident_uuid)
        action = RemediationEngine.trigger_remediation(db, inc_id, action_type)
        return f"Remediation action {action.action_type} executed with status: {action.status}"
    except Exception as e:
        return f"Error executing remediation task: {str(e)}"
    finally:
        db.close()

@celery_app.task(name="src.tasks.impact_tasks.calculate_platform_reliability")
def calculate_platform_reliability() -> str:
    db = SessionLocal()
    try:
        snapshot = CommandCenterEngine.generate_snapshot(db)
        return f"Reliability score calculated: {snapshot.platform_health_score:.2f}"
    except Exception as e:
        return f"Error calculating reliability score: {str(e)}"
    finally:
        db.close()
