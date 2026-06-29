import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from src.models.observability import DataIncident, IncidentComment
from src.models.reliability import ValidationReport
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.drift import DatasetDriftRun, ColumnDriftResult

class ObservabilityEngine:
    @staticmethod
    def evaluate_and_trigger_incidents(
        db: Session,
        dataset_version_id: uuid.UUID
    ) -> List[DataIncident]:
        """
        Scans validation reports, quality violations, anomalies, and drift.
        Triggers incidents automatically when critical reliability limits are breached.
        """
        incidents = []

        # 1. Health Score Incident
        report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == dataset_version_id).first()
        if report and report.health_score < 50.0:
            incident = DataIncident(
                dataset_version_id=dataset_version_id,
                status="OPEN",
                severity="critical",
                title="Critical Dataset Health Score Breach",
                description=f"Dataset health score dropped to {report.health_score:.2f}, breaching the threshold limit."
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)

            # Auto-comment
            db.add(IncidentComment(
                incident_id=incident.id,
                comment="System-generated: Health score critical breach alert triggered automatically."
            ))
            incidents.append(incident)

        # 2. Critical Violations Check
        latest_quality = db.query(DataQualityExecution).filter(
            DataQualityExecution.dataset_version_id == dataset_version_id,
            DataQualityExecution.status == "completed"
        ).order_by(DataQualityExecution.started_at.desc()).first()

        if latest_quality:
            violations = db.query(QualityViolation).filter(
                QualityViolation.execution_id == latest_quality.id,
                QualityViolation.severity == "critical"
            ).all()

            if violations:
                incident = DataIncident(
                    dataset_version_id=dataset_version_id,
                    status="OPEN",
                    severity="high",
                    title="Critical Quality Validation Violations",
                    description=f"Detected {len(violations)} critical validation checks failing in quality execution run."
                )
                db.add(incident)
                db.commit()
                db.refresh(incident)

                for v in violations:
                    db.add(IncidentComment(
                        incident_id=incident.id,
                        comment=f"Violation detail: Column '{v.column_name}' breached check. Message: {v.message}"
                    ))
                incidents.append(incident)

        # 3. Excessive Anomalies
        latest_anomaly = db.query(AnomalyDetectionRun).filter(
            AnomalyDetectionRun.dataset_version_id == dataset_version_id,
            AnomalyDetectionRun.status == "completed"
        ).order_by(AnomalyDetectionRun.started_at.desc()).first()

        if latest_anomaly and latest_anomaly.anomalies_found > 10:
            incident = DataIncident(
                dataset_version_id=dataset_version_id,
                status="OPEN",
                severity="medium",
                title="Excessive Outliers Detected",
                description=f"Outlier validation run detected a high density of {latest_anomaly.anomalies_found} anomalous points."
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)
            incidents.append(incident)

        db.commit()
        return incidents
