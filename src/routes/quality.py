import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.profile import DatasetProfile
from src.models.quality import DataQualityRule
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.schemas.quality import DataQualityRuleCreate, DataQualityRuleResponse, ValidationResultResponse
from src.routes.auth import get_current_user, require_role
from src.services.profiling import ProfilingEngine
from src.tasks.quality_tasks import run_quality_checks
from src.utils.audit import log_audit

router = APIRouter(prefix="/api/v1/datasets", tags=["quality"])

@router.post("/{dataset_id}/rules", response_model=DataQualityRuleResponse, status_code=status.HTTP_201_CREATED)
def create_quality_rule(
    dataset_id: uuid.UUID,
    rule_in: DataQualityRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    rule = DataQualityRule(
        dataset_id=dataset_id,
        rule_name=rule_in.rule_name,
        rule_type=rule_in.rule_type,
        threshold=rule_in.threshold,
        enabled=rule_in.enabled
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_audit(
        db=db,
        action="rule_created",
        target_type="data_quality_rule",
        target_id=rule.id,
        user_id=current_user.id
    )

    return rule

@router.get("/{dataset_id}/rules", response_model=List[DataQualityRuleResponse])
def list_quality_rules(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return db.query(DataQualityRule).filter(DataQualityRule.dataset_id == dataset_id).all()

@router.post("/versions/{version_id}/validate", response_model=ValidationResultResponse)
def validate_dataset_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == version_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Dataset version must be profiled before validation can run")

    rules = db.query(DataQualityRule).filter(DataQualityRule.dataset_id == version.dataset_id).all()
    
    profile_result = {
        "summary_metrics": profile.summary_metrics,
        "columns_metadata": profile.columns_metadata
    }

    validation_report = ProfilingEngine.validate_rules(profile_result, rules)
    return validation_report

# --- New Milestone 2 Quality Run API Endpoints ---

@router.post("/versions/{version_id}/quality/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_quality_run(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    # Create execution record in pending
    exec_record = DataQualityExecution(
        dataset_version_id=version_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(exec_record)
    db.commit()
    db.refresh(exec_record)

    # Trigger via Celery task
    run_quality_checks.delay(str(version_id))

    return {
        "execution_id": exec_record.id,
        "status": exec_record.status,
        "message": "Quality checks triggered successfully"
    }

@router.get("/versions/{version_id}/quality")
def get_quality_executions(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    executions = db.query(DataQualityExecution).filter(
        DataQualityExecution.dataset_version_id == version_id
    ).order_by(DataQualityExecution.started_at.desc()).all()
    return executions

@router.get("/executions/{execution_id}")
def get_quality_execution_details(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    execution = db.query(DataQualityExecution).filter(DataQualityExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Quality run execution not found")
    return {
        "id": execution.id,
        "dataset_version_id": execution.dataset_version_id,
        "status": execution.status,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "summary": execution.summary_json,
        "violations": db.query(QualityViolation).filter(QualityViolation.execution_id == execution_id).all()
    }

@router.get("/violations/all")
def get_all_quality_violations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    violations = db.query(QualityViolation).order_by(QualityViolation.created_at.desc()).all()
    return violations
