import uuid
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.retention import RetentionPolicy, DataPurgeExecution
from src.models.profile import DatasetProfile

class RetentionEngine:

    @staticmethod
    def configure_retention(db: Session, dataset_id: uuid.UUID, days: int) -> RetentionPolicy:
        policy = db.query(RetentionPolicy).filter(RetentionPolicy.dataset_id == dataset_id).first()
        if not policy:
            policy = RetentionPolicy(dataset_id=dataset_id, retention_days=days)
            db.add(policy)
        else:
            policy.retention_days = days
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def execute_purges(db: Session, dataset_id: uuid.UUID) -> DataPurgeExecution:
        policy = db.query(RetentionPolicy).filter(RetentionPolicy.dataset_id == dataset_id).first()
        days = policy.retention_days if policy else 30

        limit_date = datetime.utcnow() - timedelta(days=days)

        from src.models.dataset import DatasetVersion
        old_profiles = db.query(DatasetProfile).join(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id,
            DatasetProfile.created_at < limit_date
        )

        purged_count = old_profiles.count()
        profile_ids = [p.id for p in old_profiles.all()]

        # Execute purge
        if profile_ids:
            db.query(DatasetProfile).filter(DatasetProfile.id.in_(profile_ids)).delete(synchronize_session=False)


        exec_record = DataPurgeExecution(
            dataset_id=dataset_id,
            purged_records_count=purged_count,
            status="SUCCESS"
        )
        db.add(exec_record)
        db.commit()
        db.refresh(exec_record)
        return exec_record
