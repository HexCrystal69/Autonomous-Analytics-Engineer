import uuid
from typing import Optional
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.copilot_engine import CopilotEngine

@celery_app.task(name="src.tasks.intelligence_tasks.generate_incident_summary")
def generate_incident_summary(incident_uuid: str) -> str:
    db = SessionLocal()
    try:
        inc_id = uuid.UUID(incident_uuid)
        analysis = CopilotEngine.explain_incident(db, inc_id)
        return f"Incident analysis generated: {analysis.id}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.close()

@celery_app.task(name="src.tasks.intelligence_tasks.generate_dataset_summary")
def generate_dataset_summary(dataset_uuid: str) -> str:
    db = SessionLocal()
    try:
        ds_id = uuid.UUID(dataset_uuid)
        analysis = CopilotEngine.explain_dataset(db, ds_id)
        return f"Dataset analysis generated: {analysis.id}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.close()
