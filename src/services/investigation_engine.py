import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.investigation import Investigation, InvestigationFinding, InvestigationSLA
from src.models.reliability import ValidationReport

class InvestigationEngine:

    @staticmethod
    def trigger_investigation(
        db: Session,
        dataset_id: uuid.UUID,
        title: str,
        description: str,
        priority: str = "medium",
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> Investigation:
        investigation = Investigation(
            dataset_id=dataset_id,
            title=title,
            description=description,
            status="OPEN",
            priority=priority,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)

        # Create SLA
        sla_hours = 24
        if priority == "critical":
            sla_hours = 12
        elif priority == "low":
            sla_hours = 48

        sla = InvestigationSLA(
            investigation_id=investigation.id,
            target_resolution_hours=sla_hours,
            breached=False
        )
        db.add(sla)
        db.commit()

        return investigation

    @staticmethod
    def add_finding(
        db: Session,
        investigation_id: uuid.UUID,
        finding_type: str,
        evidence_json: dict,
        source_table: Optional[str] = None,
        source_record_id: Optional[uuid.UUID] = None,
        confidence: float = 100.0,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> InvestigationFinding:
        finding = InvestigationFinding(
            investigation_id=investigation_id,
            finding_type=finding_type,
            evidence_json=evidence_json,
            source_table=source_table,
            source_record_id=source_record_id,
            confidence=confidence,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(finding)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def update_status(
        db: Session,
        investigation_id: uuid.UUID,
        status: str,
        notes: Optional[str] = None,
        operator: Optional[str] = None
    ) -> Optional[Investigation]:
        inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not inv:
            return None

        inv.status = status
        if status in ["RESOLVED", "CLOSED"]:
            inv.resolution_notes = notes
            inv.resolved_by = operator
            inv.resolved_at = datetime.utcnow()

            # Update SLA actuals
            if inv.sla:
                diff = inv.resolved_at - inv.created_at
                hours = int(diff.total_seconds() / 3600)
                inv.sla.actual_resolution_hours = hours
                inv.sla.breached = hours > inv.sla.target_resolution_hours
                
        db.commit()
        db.refresh(inv)
        return inv
