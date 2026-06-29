import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.certification import DatasetCertification
from src.services.certification_engine import CertificationEngine

router = APIRouter(prefix="/api/v1/certifications", tags=["Dataset Certification"])


class CertificationTriggerSchema(BaseModel):
    dataset_id: uuid.UUID
    approved_by: Optional[str] = "Admin Auditor"
    notes: Optional[str] = ""

class CertificationResponseSchema(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    certification_level: str
    approved_by: str
    approved_at: str
    notes: Optional[str]

    class Config:
        from_attributes = True

@router.post("", status_code=status.HTTP_201_CREATED)
def trigger_certification(payload: CertificationTriggerSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    cert = CertificationEngine.evaluate_certification(
        db,
        payload.dataset_id,
        payload.approved_by,
        payload.notes
    )
    return {
        "id": cert.id,
        "dataset_id": cert.dataset_id,
        "certification_level": cert.certification_level,
        "approved_by": cert.approved_by,
        "approved_at": cert.approved_at.isoformat(),
        "notes": cert.notes
    }

@router.get("")
def list_certifications(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    certs = db.query(DatasetCertification).all()
    return [{
        "id": c.id,
        "dataset_id": c.dataset_id,
        "certification_level": c.certification_level,
        "approved_by": c.approved_by,
        "approved_at": c.approved_at.isoformat(),
        "notes": c.notes
    } for c in certs]

@router.get("/{dataset_id}")
def get_certification(dataset_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    cert = db.query(DatasetCertification).filter(DatasetCertification.dataset_id == dataset_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification details not found for dataset")
    return {
        "id": cert.id,
        "dataset_id": cert.dataset_id,
        "certification_level": cert.certification_level,
        "approved_by": cert.approved_by,
        "approved_at": cert.approved_at.isoformat(),
        "notes": cert.notes
    }
