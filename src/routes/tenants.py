import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.tenant import Tenant, TenantMember

router = APIRouter(prefix="/api/v1/tenants", tags=["Multi-Tenancy"])

class TenantCreateSchema(BaseModel):
    name: str

@router.post("", status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tenant = Tenant(name=payload.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name}

@router.get("")
def list_tenants(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tenants = db.query(Tenant).all()
    return [{"id": t.id, "name": t.name} for t in tenants]

@router.get("/{id}/members")
def get_tenant_members(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tenant = db.query(Tenant).filter(Tenant.id == id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return [{"id": m.id, "user_id": m.user_id, "role": m.role} for m in tenant.members]
