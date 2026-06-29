import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON
from datetime import datetime
from src.database import Base

class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id = Column(Uuid, ForeignKey("data_incidents.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String, nullable=False) # reprofile_dataset, rerun_quality_checks, rerun_drift_analysis, recompute_scorecard, recalculate_sla
    status = Column(String, default="PENDING", nullable=False) # PENDING, EXECUTING, SUCCESS, FAILED
    executed_at = Column(DateTime, nullable=True)
    details_json = Column(JSON, nullable=True)
