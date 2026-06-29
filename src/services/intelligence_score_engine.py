import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.models.dashboard import ReliabilityDashboardSnapshot
from src.models.sla import DatasetSLA
from src.models.governance import ComplianceSnapshot
from src.models.observability import DataIncident
from src.models.contract import ContractViolation
from src.models.workflow import WorkflowExecution

class IntelligenceScoreEngine:

    @staticmethod
    def calculate_intelligence_score(db: Session) -> Dict[str, Any]:
        # 1. Reliability
        latest_dash = db.query(ReliabilityDashboardSnapshot).order_by(ReliabilityDashboardSnapshot.created_at.desc()).first()
        reliability = latest_dash.platform_health_score if latest_dash else 100.0

        # 2. SLA Compliance
        slas = db.query(DatasetSLA).all()
        sla_comp = 100.0
        if slas:
            from src.services.sla_engine import SLAEngine
            total_sla = sum(SLAEngine.check_sla(db, s.dataset_id).compliance_pct for s in slas)
            sla_comp = total_sla / len(slas)

        # 3. Governance Compliance
        snapshots = db.query(ComplianceSnapshot).all()
        gov_comp = 100.0
        if snapshots:
            gov_comp = sum(s.compliance_score for s in snapshots) / len(snapshots)

        # 4. Incident Stability
        open_inc = db.query(DataIncident).filter(DataIncident.status == "OPEN").count()
        inc_stability = max(0.0, 100.0 - (open_inc * 10.0))

        # 5. Contract Compliance
        violations = db.query(ContractViolation).count()
        contract_comp = max(0.0, 100.0 - (violations * 10.0))

        # 6. Workflow Success Rate
        executions = db.query(WorkflowExecution).all()
        wf_success = 100.0
        if executions:
            success = sum(1 for e in executions if e.status == "SUCCESS")
            wf_success = (success / len(executions)) * 100.0

        score = (
            0.25 * reliability +
            0.20 * sla_comp +
            0.20 * gov_comp +
            0.15 * inc_stability +
            0.10 * contract_comp +
            0.10 * wf_success
        )
        score = max(0.0, min(100.0, score))

        if score >= 90.0:
            rating = "Excellent"
        elif score >= 75.0:
            rating = "Good"
        elif score >= 50.0:
            rating = "Warning"
        else:
            rating = "Critical"

        return {
            "score": score,
            "rating": rating,
            "components": {
                "reliability": reliability,
                "sla_compliance": sla_comp,
                "governance_compliance": gov_comp,
                "incident_stability": inc_stability,
                "contract_compliance": contract_comp,
                "workflow_success_rate": wf_success
            }
        }
