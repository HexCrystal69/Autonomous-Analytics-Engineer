import uuid
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.contract_engine import ContractEngine
from src.services.governance_engine import GovernanceEngine

@celery_app.task(name="src.tasks.governance_tasks.evaluate_contracts")
def evaluate_contracts(dataset_version_uuid: str) -> str:
    db = SessionLocal()
    try:
        ver_id = uuid.UUID(dataset_version_uuid)
        violations = ContractEngine.validate_version(db, ver_id)
        return f"Contract evaluation finished. Logged {len(violations)} violations."
    except Exception as e:
        return f"Error in contract evaluation task: {str(e)}"
    finally:
        db.close()
