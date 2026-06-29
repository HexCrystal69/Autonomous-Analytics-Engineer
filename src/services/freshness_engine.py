import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from sqlalchemy import func
from src.models.freshness import DatasetFreshnessRecord

class FreshnessEngine:
    @staticmethod
    def log_freshness(
        db: Session,
        dataset_id: uuid.UUID,
        expected_time: datetime,
        actual_time: Optional[datetime] = None
    ) -> DatasetFreshnessRecord:
        """
        Logs actual and expected dataset refresh times, calculates delay, and assigns status.
        """
        act_time = actual_time or datetime.utcnow()
        delay = int((act_time - expected_time).total_seconds() / 60.0)
        delay = max(0, delay)

        # Status categorization
        if delay == 0:
            status = "on_time"
        elif delay < 60:
            status = "late"
        else:
            status = "critical"

        record = DatasetFreshnessRecord(
            dataset_id=dataset_id,
            expected_refresh_time=expected_time,
            actual_refresh_time=act_time,
            delay_minutes=delay,
            status=status
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_metrics(db: Session, dataset_id: uuid.UUID) -> dict:
        """Calculates freshness score, SLA breach flag, and average delay minutes."""
        records = db.query(DatasetFreshnessRecord).filter(
            DatasetFreshnessRecord.dataset_id == dataset_id
        ).order_by(DatasetFreshnessRecord.recorded_at.desc()).all()

        if not records:
            return {
                "freshness_score": 100.0,
                "sla_breach": False,
                "average_delay_minutes": 0.0
            }

        latest = records[0]
        sla_breach = latest.status in ["late", "critical"]
        
        # Freshness score formula: 100 - latest delay, clamped
        score = float(max(0.0, 100.0 - latest.delay_minutes))

        avg_delay = db.query(func.avg(DatasetFreshnessRecord.delay_minutes)).filter(
            DatasetFreshnessRecord.dataset_id == dataset_id
        ).scalar()

        return {
            "freshness_score": score,
            "sla_breach": sla_breach,
            "average_delay_minutes": round(float(avg_delay), 2) if avg_delay is not None else 0.0
        }
