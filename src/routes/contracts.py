import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.contract import DataContract, DataContractRule, ContractVersion, ContractViolation
from src.services.contract_engine import ContractEngine

router = APIRouter(prefix="/api/v1/contracts", tags=["Data Contracts"])


class RuleSchema(BaseModel):
    rule_type: str
    column_name: Optional[str] = None
    expected_value: Optional[str] = None
    severity: Optional[str] = "high"

class ContractCreateSchema(BaseModel):
    dataset_id: uuid.UUID
    name: str
    owner: str
    description: Optional[str] = None
    contract_version: Optional[str] = "1.0.0"
    rules: List[RuleSchema]

class ContractResponseSchema(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    owner: str
    description: Optional[str] = None
    contract_version: str
    status: str

    class Config:
        from_attributes = True

@router.post("", response_model=ContractResponseSchema, status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreateSchema, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    rules_dict = [r.dict() for r in payload.rules]
    contract = ContractEngine.create_contract(
        db,
        payload.dataset_id,
        payload.name,
        payload.owner,
        payload.description,
        payload.contract_version,
        rules_dict
    )
    return contract

@router.get("", response_model=List[ContractResponseSchema])
def list_contracts(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DataContract).all()

@router.get("/{id}", response_model=ContractResponseSchema)
def get_contract(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    contract = db.query(DataContract).filter(DataContract.id == id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@router.patch("/{id}", response_model=ContractResponseSchema)
def update_contract_status(id: uuid.UUID, status: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    contract = db.query(DataContract).filter(DataContract.id == id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if status not in ["draft", "active", "deprecated"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    contract.status = status
    db.commit()
    db.refresh(contract)
    return contract

@router.get("/{id}/versions")
def get_contract_versions(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    versions = db.query(ContractVersion).filter(ContractVersion.contract_id == id).all()
    return [{"id": v.id, "version": v.version, "schema_hash": v.schema_hash, "created_at": v.created_at} for v in versions]

@router.get("/{id}/violations")
def get_contract_violations(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Find all rules linked to this contract
    rules = db.query(DataContractRule).filter(DataContractRule.contract_id == id).all()
    rule_ids = [r.id for r in rules]
    violations = db.query(ContractViolation).filter(ContractViolation.contract_rule_id.in_(rule_ids)).all()
    return [{
        "id": v.id,
        "contract_rule_id": v.contract_rule_id,
        "dataset_version_id": v.dataset_version_id,
        "severity": v.severity,
        "message": v.message,
        "created_at": v.created_at
    } for v in violations]
