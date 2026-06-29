import uuid
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion, DatasetTag
from src.models.job import ProfilingJob
from src.models.profile import DatasetProfile
from src.models.lineage import DatasetLineage
from src.schemas.dataset import DatasetResponse, DatasetVersionResponse, DatasetListResponse
from src.schemas.job import ProfilingJobResponse, DatasetProfileResponse
from src.routes.auth import get_current_user, require_role
from src.services.storage import StorageProviderFactory
from src.tasks.profile_tasks import run_dataset_profiling
from src.config import settings
from src.utils.audit import log_audit

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])

@router.post("/upload", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
def upload_dataset(
    name: str = Form(...),
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None), # Comma separated list of tags
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    # Validate file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Save file using Storage Provider
    storage_provider = StorageProviderFactory.get_provider()
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = storage_provider.save_file(file.file, unique_filename)

    # Create dataset
    dataset = Dataset(name=name, owner_id=current_user.id)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Handle optional tags
    if tags:
        for tag_name in tags.split(","):
            tag_name = tag_name.strip()
            if tag_name:
                db.add(DatasetTag(dataset_id=dataset.id, tag_name=tag_name))
        db.commit()

    # Log audit: dataset uploaded
    log_audit(
        db=db,
        action="dataset_uploaded",
        target_type="dataset",
        target_id=dataset.id,
        user_id=current_user.id
    )

    # Create first dataset version
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        file_path=file_path,
        filename=file.filename,
        mime_type=file.content_type or "text/csv",
        file_size=size
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Log audit: version created
    log_audit(
        db=db,
        action="version_created",
        target_type="dataset_version",
        target_id=version.id,
        user_id=current_user.id
    )

    # Auto-trigger profiling job
    job = ProfilingJob(dataset_version_id=version.id, status="PENDING")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to Celery
    celery_task = run_dataset_profiling.delay(str(job.id))
    job.task_id = celery_task.id
    db.commit()

    return version

@router.post("/{dataset_id}/version", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
def upload_dataset_version(
    dataset_id: UUID,
    file: UploadFile = File(...),
    parent_version_id: Optional[UUID] = Form(None),
    transformation_type: Optional[str] = Form("UPLOAD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Determine version number
    latest_version = db.query(DatasetVersion)\
        .filter(DatasetVersion.dataset_id == dataset_id)\
        .order_by(DatasetVersion.version_number.desc())\
        .first()
    
    next_ver = (latest_version.version_number + 1) if latest_version else 1

    storage_provider = StorageProviderFactory.get_provider()
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = storage_provider.save_file(file.file, unique_filename)

    version = DatasetVersion(
        dataset_id=dataset_id,
        version_number=next_ver,
        file_path=file_path,
        filename=file.filename,
        mime_type=file.content_type or "text/csv",
        file_size=size
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Log audit: version created
    log_audit(
        db=db,
        action="version_created",
        target_type="dataset_version",
        target_id=version.id,
        user_id=current_user.id
    )

    # Lineage tracking
    parent_id = parent_version_id or (latest_version.id if latest_version else None)
    if parent_id:
        lineage = DatasetLineage(
            parent_dataset_version_id=parent_id,
            child_dataset_version_id=version.id,
            transformation_type=transformation_type or "UPLOAD"
        )
        db.add(lineage)
        db.commit()

    # Trigger profiling job
    job = ProfilingJob(dataset_version_id=version.id, status="PENDING")
    db.add(job)
    db.commit()
    db.refresh(job)

    celery_task = run_dataset_profiling.delay(str(job.id))
    job.task_id = celery_task.id
    db.commit()

    return version

@router.get("", response_model=List[DatasetListResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    datasets = db.query(Dataset).offset(skip).limit(limit).all()
    results = []
    for d in datasets:
        # Find latest version
        latest_ver = db.query(DatasetVersion)\
            .filter(DatasetVersion.dataset_id == d.id)\
            .order_by(DatasetVersion.version_number.desc())\
            .first()
        results.append({
            "id": d.id,
            "name": d.name,
            "owner_id": d.owner_id,
            "created_at": d.created_at,
            "latest_version": latest_ver
        })
    return results

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.post("/versions/{version_id}/profile", response_model=ProfilingJobResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_profiling(
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    version = db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    job = ProfilingJob(dataset_version_id=version.id, status="PENDING")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Log audit: profile manual trigger
    log_audit(
        db=db,
        action="profile_started",
        target_type="dataset_version",
        target_id=version.id,
        user_id=current_user.id
    )

    celery_task = run_dataset_profiling.delay(str(job.id))
    job.task_id = celery_task.id
    db.commit()
    db.refresh(job)

    return job

@router.get("/versions/{version_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == version_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not calculated yet or version does not exist")
    return profile

@router.get("/jobs/{job_id}", response_model=ProfilingJobResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(ProfilingJob).filter(ProfilingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Profiling job not found")
    return job
