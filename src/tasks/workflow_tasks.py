import uuid
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.workflow_engine import WorkflowEngine
from src.services.investigation_engine import InvestigationEngine

@celery_app.task(name="src.tasks.workflow_tasks.execute_workflow")
def execute_workflow(workflow_uuid: str) -> str:
    db = SessionLocal()
    try:
        wf_id = uuid.UUID(workflow_uuid)
        exec_record = WorkflowEngine.trigger_workflow(db, wf_id, {})
        return f"Workflow execution finished: {exec_record.id} with status {exec_record.status}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.close()

@celery_app.task(name="src.tasks.workflow_tasks.run_automated_investigation")
def run_automated_investigation(dataset_uuid: str, reason: str) -> str:
    db = SessionLocal()
    try:
        ds_id = uuid.UUID(dataset_uuid)
        inv = InvestigationEngine.trigger_investigation(db, ds_id, "Automated Alert Investigation", reason, "high")
        return f"Automated investigation created: {inv.id}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        db.close()
