import uuid
from datetime import datetime
from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.job import ProfilingJob
from src.models.dataset import DatasetVersion
from src.models.profile import DatasetProfile
from src.models.snapshot import ProfileSnapshot
from src.services.profiling import ProfilingEngine
from src.utils.audit import log_audit

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def run_dataset_profiling(self, job_id: str) -> str:
    """Celery task to profile a dataset version and save statistics."""
    db = SessionLocal()
    try:
        job = db.query(ProfilingJob).filter(ProfilingJob.id == uuid.UUID(job_id)).first()
        if not job:
            return f"Job {job_id} not found."

        job.status = "PROCESSING"
        job.task_id = self.request.id
        job.started_at = datetime.utcnow()
        db.commit()

        # Log audit: profile started
        log_audit(
            db=db,
            action="profile_started",
            target_type="dataset_version",
            target_id=job.dataset_version_id
        )

        version = db.query(DatasetVersion).filter(DatasetVersion.id == job.dataset_version_id).first()
        if not version:
            raise ValueError(f"Dataset version {job.dataset_version_id} not found.")

        # Compute profiles
        profile_data = ProfilingEngine.profile(version.file_path, version.mime_type)

        # Update row and col count in version
        version.row_count = profile_data["summary_metrics"]["row_count"]
        version.column_count = profile_data["summary_metrics"]["column_count"]

        # Create or update profile
        existing_profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == version.id).first()
        if existing_profile:
            existing_profile.summary_metrics = profile_data["summary_metrics"]
            existing_profile.columns_metadata = profile_data["columns_metadata"]
            existing_profile.created_at = datetime.utcnow()
        else:
            profile = DatasetProfile(
                dataset_version_id=version.id,
                summary_metrics=profile_data["summary_metrics"],
                columns_metadata=profile_data["columns_metadata"]
            )
            db.add(profile)

        # Save snapshot history
        snapshot = ProfileSnapshot(
            dataset_version_id=version.id,
            summary_metrics=profile_data["summary_metrics"]
        )
        db.add(snapshot)

        # Update Job Status
        job.status = "SUCCESS"
        job.completed_at = datetime.utcnow()
        db.commit()

        # Log audit: profile completed
        log_audit(
            db=db,
            action="profile_completed",
            target_type="dataset_version",
            target_id=version.id
        )

        return f"Profiling completed successfully for job {job_id}"

    except Exception as exc:
        db.rollback()
        # Retrieve again to update error status
        job = db.query(ProfilingJob).filter(ProfilingJob.id == uuid.UUID(job_id)).first()
        if job:
            job.status = "FAILED"
            job.completed_at = datetime.utcnow()
            job.error_message = str(exc)
            db.commit()
            
            # Log audit: profile failed
            try:
                log_audit(
                    db=db,
                    action="profile_failed",
                    target_type="dataset_version",
                    target_id=job.dataset_version_id,
                    metadata_json={"error": str(exc)}
                )
            except Exception:
                pass
        raise exc
    finally:
        db.close()
