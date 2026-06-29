import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.investigation import Investigation
from src.services.investigation_engine import InvestigationEngine

router = APIRouter(prefix="/api/v1/investigations", tags=["Investigation Center"])

class InvestigationCreateSchema(BaseModel):
    dataset_id: uuid.UUID
    title: str
    description: str
    priority: Optional[str] = "medium"

@router.post("", status_code=status.HTTP_201_CREATED)
def create_investigation(payload: InvestigationCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    inv = InvestigationEngine.trigger_investigation(
        db, payload.dataset_id, payload.title, payload.description, payload.priority
    )
    return {"id": inv.id, "title": inv.title, "status": inv.status, "priority": inv.priority}

@router.get("")
def list_investigations(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    invs = db.query(Investigation).all()
    return [{"id": i.id, "title": i.title, "status": i.status, "priority": i.priority} for i in invs]

@router.get("/{id}")
def get_investigation(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "id": inv.id,
        "title": inv.title,
        "description": inv.description,
        "status": inv.status,
        "priority": inv.priority,
        "findings": [{"id": f.id, "type": f.finding_type, "confidence": f.confidence} for f in inv.findings]
    }

@router.patch("/{id}")
def patch_investigation(
    id: uuid.UUID,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    inv = InvestigationEngine.update_status(db, id, status, notes, current_user.email)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {"id": inv.id, "status": inv.status}
