import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session
from src.models.dashboard import ReliabilityDashboardSnapshot
from src.models.dataset import Dataset
from src.models.observability import DataIncident
from src.models.reliability import ValidationReport
from src.models.sla import DatasetSLA
from src.models.freshness import DatasetFreshnessRecord
from src.services.sla_engine import SLAEngine

class CommandCenterEngine:
    @staticmethod
    def generate_snapshot(db: Session) -> ReliabilityDashboardSnapshot:
        datasets_monitored = db.query(Dataset).count()
        active_incidents = db.query(DataIncident).filter(DataIncident.status == "OPEN").count()
        critical_incidents = db.query(DataIncident).filter(
            DataIncident.status == "OPEN",
            DataIncident.severity == "critical"
        ).count()

        # Quality, health, drift, anomaly averages
        reports = db.query(ValidationReport).all()
        quality_avg = 100.0
        health_avg = 100.0
        drift_avg = 0.0
        anomaly_avg = 0.0

        if reports:
            quality_avg = sum(r.quality_score for r in reports) / len(reports)
            health_avg = sum(r.health_score for r in reports) / len(reports)
            drift_avg = sum(r.drift_score for r in reports) / len(reports)
            anomaly_avg = sum(r.anomaly_score for r in reports) / len(reports)

        # SLA Compliance average
        slas = db.query(DatasetSLA).all()
        sla_compliance_pct = 100.0
        if slas:
            sum_comp = 0.0
            for s in slas:
                res = SLAEngine.check_sla(db, s.dataset_id)
                sum_comp += res.compliance_pct
            sla_compliance_pct = sum_comp / len(slas)

        # Freshness rating (100 - critical delay count percentage)
        freshness_records = db.query(DatasetFreshnessRecord).all()
        freshness_score = 100.0
        if freshness_records:
            crits = sum(1 for f in freshness_records if f.status == "critical")
            freshness_score = max(0.0, 100.0 - (crits / len(freshness_records)) * 100.0)

        # Incident stability rating
        incident_stability = max(0.0, 100.0 - (critical_incidents * 15.0) - (active_incidents * 5.0))

        # Combined Platform Reliability Score calculation
        score = (
            (0.30 * quality_avg) +
            (0.25 * health_avg) +
            (0.20 * sla_compliance_pct) +
            (0.15 * freshness_score) +
            (0.10 * incident_stability)
        )

        snapshot = ReliabilityDashboardSnapshot(
            platform_health_score=score,
            datasets_monitored=datasets_monitored,
            active_incidents=active_incidents,
            critical_incidents=critical_incidents,
            sla_compliance_pct=sla_compliance_pct,
            quality_avg=quality_avg,
            drift_avg=drift_avg,
            anomaly_avg=anomaly_avg
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
