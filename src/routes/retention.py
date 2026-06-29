import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.retention import RetentionPolicy, DataPurgeExecution
from src.services.retention_engine import RetentionEngine

router = APIRouter(prefix="/api/v1/retention", tags=["Data Expiration Lifecycle"])

class RetentionConfigureSchema(BaseModel):
    dataset_id: uuid.UUID
    retention_days: int

@router.post("", status_code=status.HTTP_201_CREATED)
def configure_retention(payload: RetentionConfigureSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    policy = RetentionEngine.configure_retention(db, payload.dataset_id, payload.retention_days)
    return {"id": policy.id, "dataset_id": policy.dataset_id, "retention_days": policy.retention_days}

@router.post("/execute/{dataset_id}")
def execute_purge(dataset_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    exec_record = RetentionEngine.execute_purges(db, dataset_id)
    return {"id": exec_record.id, "purged_count": exec_record.purged_records_count, "status": exec_record.status}

@router.get("/executions")
def list_executions(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    execs = db.query(DataPurgeExecution).all()
    return [{"id": e.id, "dataset_id": e.dataset_id, "status": e.status} for e in execs]
