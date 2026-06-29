import uuid
from datetime import datetime, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import Session
from src.models.certification import DatasetCertification
from src.models.dataset import DatasetVersion
from src.models.reliability import ValidationReport
from src.models.sla import DatasetSLA
from src.models.observability import DataIncident
from src.services.sla_engine import SLAEngine

class CertificationEngine:
    @staticmethod
    def evaluate_certification(
        db: Session,
        dataset_id: uuid.UUID,
        approved_by: str = "System Classifier",
        notes: str = ""
    ) -> DatasetCertification:
        # Find latest dataset version
        latest_ver = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id
        ).order_by(DatasetVersion.version_number.desc()).first()

        if not latest_ver:
            # Bronze defaults for empty datasets
            cert = DatasetCertification(
                dataset_id=dataset_id,
                certification_level="bronze",
                approved_by=approved_by,
                notes="Default classification for new dataset.",
                expires_at=datetime.utcnow() + timedelta(days=90)
            )
            db.add(cert)
            db.commit()
            db.refresh(cert)
            return cert

        # Fetch quality metrics validation report
        report = db.query(ValidationReport).filter(
            ValidationReport.dataset_version_id == latest_ver.id
        ).first()

        # Fetch active incidents
        active_incidents = db.query(DataIncident).filter(
            DataIncident.dataset_version_id == latest_ver.id,
            DataIncident.status == "OPEN"
        ).count()

        # Evaluate SLA compliance
        sla_comp = 100.0
        sla_eval = db.query(DatasetSLA).filter(DatasetSLA.dataset_id == dataset_id).first()
        if sla_eval:
            sla_res = SLAEngine.check_sla(db, dataset_id)
            sla_comp = sla_res.compliance_pct

        health = report.health_score if report else 100.0
        quality = report.quality_score if report else 100.0
        drift = report.drift_score if report else 0.0

        # Classification rule conditions
        if health >= 90.0 and quality >= 90.0 and drift <= 0.2 and sla_comp == 100.0 and active_incidents == 0:
            level = "platinum"
        elif health >= 80.0 and quality >= 80.0 and drift <= 0.3 and sla_comp >= 90.0 and active_incidents == 0:
            level = "gold"
        elif health >= 65.0 and quality >= 65.0 and drift <= 0.5 and active_incidents <= 1:
            level = "silver"
        else:
            level = "bronze"

        # Deprecate old certification
        db.query(DatasetCertification).filter(DatasetCertification.dataset_id == dataset_id).delete()

        cert = DatasetCertification(
            dataset_id=dataset_id,
            certification_level=level,
            approved_by=approved_by,
            notes=notes or f"Auto-computed: health={health:.1f}, quality={quality:.1f}, SLA={sla_comp:.1f}%, incidents={active_incidents}",
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        return cert
