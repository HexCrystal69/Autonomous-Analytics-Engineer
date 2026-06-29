import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.sla import DatasetSLA
from src.models.dataset import DatasetVersion
from src.models.reliability import ValidationReport

class SLAEngine:
    @staticmethod
    def check_sla(db: Session, dataset_id: uuid.UUID) -> DatasetSLA:
        """
        Calculates compliance percent for a dataset governed by SLA targets.
        Freshness compliance: Upload interval < target_freshness_hours.
        Quality compliance: validation report quality_score >= target_quality_score.
        """
        sla = db.query(DatasetSLA).filter(DatasetSLA.dataset_id == dataset_id).first()
        if not sla:
            # Create default SLA if not exists
            sla = DatasetSLA(
                dataset_id=dataset_id,
                target_freshness_hours=24,
                target_quality_score=95.0,
                compliance_pct=100.0
            )
            db.add(sla)
            db.commit()
            db.refresh(sla)

        versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
        if not versions:
            sla.compliance_pct = 0.0
            sla.checked_at = datetime.utcnow()
            db.commit()
            return sla

        latest_ver = versions[0]

        # 1. Freshness check
        time_since_upload = datetime.utcnow() - latest_ver.created_at
        freshness_compliant = time_since_upload <= timedelta(hours=sla.target_freshness_hours)


        # 2. Quality check
        report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == latest_ver.id).first()
        quality_compliant = False
        if report:
            quality_compliant = report.quality_score >= sla.target_quality_score

        # Compliance score computation
        met_targets = 0
        total_targets = 2

        if freshness_compliant:
            met_targets += 1
        if quality_compliant:
            met_targets += 1

        compliance_pct = (met_targets / total_targets) * 100.0

        sla.compliance_pct = float(compliance_pct)
        sla.checked_at = datetime.utcnow()
        db.commit()
        return sla
