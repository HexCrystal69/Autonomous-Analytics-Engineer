import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.workflow import WorkflowDefinition, WorkflowExecution
from src.services.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow Studio"])

class WorkflowCreateSchema(BaseModel):
    name: str
    trigger_type: str

class WorkflowDependencySchema(BaseModel):
    parent_workflow_id: uuid.UUID
    child_workflow_id: uuid.UUID
    dependency_type: Optional[str] = "triggers"

@router.post("", status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    wf = WorkflowEngine.create_workflow(db, payload.name, payload.trigger_type)
    return {"id": wf.id, "name": wf.name, "trigger_type": wf.trigger_type}

@router.post("/dependency", status_code=status.HTTP_201_CREATED)
def add_dependency(payload: WorkflowDependencySchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    dep = WorkflowEngine.add_dependency(db, payload.parent_workflow_id, payload.child_workflow_id, payload.dependency_type)
    return {"id": dep.id, "parent_workflow_id": dep.parent_workflow_id, "child_workflow_id": dep.child_workflow_id}

@router.get("")
def list_workflows(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    wfs = db.query(WorkflowDefinition).all()
    return [{"id": w.id, "name": w.name, "trigger_type": w.trigger_type, "enabled": w.enabled} for w in wfs]

@router.post("/{id}/execute")
def execute_workflow(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        exec_record = WorkflowEngine.trigger_workflow(db, id, {})
        return {
            "execution_id": exec_record.id,
            "status": exec_record.status,
            "validation_status": exec_record.workflow_validation_status,
            "validation_message": exec_record.validation_message
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/executions")
def list_executions(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    execs = db.query(WorkflowExecution).all()
    return [{"id": e.id, "status": e.status, "validation_status": e.workflow_validation_status, "retry_count": e.retry_count} for e in execs]
