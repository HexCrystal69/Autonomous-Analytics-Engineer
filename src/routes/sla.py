import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.sla import DatasetSLA
from src.routes.auth import get_current_user

router = APIRouter(prefix="/api/v1/sla", tags=["sla"])

@router.get("")
def list_slas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    slas = db.query(DatasetSLA).all()
    return slas

@router.get("/{dataset_id}")
def get_sla(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sla = db.query(DatasetSLA).filter(DatasetSLA.dataset_id == dataset_id).first()
    if not sla:
        raise HTTPException(status_code=404, detail="SLA record not found for dataset")
    return sla
