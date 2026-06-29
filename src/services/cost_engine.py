import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.models.cost import CloudCostSnapshot, ComputeUsageMetric, StorageUsageMetric

class CostEngine:

    @staticmethod
    def log_compute_cost(db: Session, resource_id: str, resource_type: str, cpu_ms: float) -> ComputeUsageMetric:
        # Assumes $0.0001 per cpu millisecond unit cost
        cost = cpu_ms * 0.0001
        metric = ComputeUsageMetric(
            resource_id=resource_id,
            resource_type=resource_type,
            cpu_milliseconds=cpu_ms,
            estimated_cost=cost
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def calculate_tenant_cost(db: Session) -> Dict[str, Any]:
        compute_cost = sum(m.estimated_cost for m in db.query(ComputeUsageMetric).all())
        storage_cost = sum(m.estimated_monthly_cost for m in db.query(StorageUsageMetric).all())
        total = compute_cost + storage_cost

        return {
            "total_estimated_spend": total,
            "compute": compute_cost,
            "storage": storage_cost
        }
