import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/api/v1/feature-flags", tags=["Feature Management"])

class FeatureFlagCreateSchema(BaseModel):
    key: str
    description: str
    rollout_percentage: Optional[int] = 100

@router.post("", status_code=status.HTTP_201_CREATED)
def create_flag(payload: FeatureFlagCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    flag = FeatureFlag(key=payload.key, description=payload.description, rollout_percentage=payload.rollout_percentage)
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return {"id": flag.id, "key": flag.key, "enabled": flag.enabled}

@router.get("")
def list_flags(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    flags = db.query(FeatureFlag).all()
    return [{"id": f.id, "key": f.key, "enabled": f.enabled} for f in flags]
