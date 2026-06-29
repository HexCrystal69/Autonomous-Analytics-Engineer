import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models.recommendation import Recommendation
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.drift import DatasetDriftRun, ColumnDriftResult

class RecommendationEngine:
    @staticmethod
    def generate(
        db: Session,
        dataset_version_id: uuid.UUID
    ) -> List[Recommendation]:
        """
        Dynamically generates explainable recommendations based on violations, anomalies, and drift.
        Persists and returns Recommendation models.
        """
        recommendations = []

        # 1. Inspect Quality Violations
        latest_quality = db.query(DataQualityExecution).filter(
            DataQualityExecution.dataset_version_id == dataset_version_id,
            DataQualityExecution.status == "completed"
        ).order_by(DataQualityExecution.started_at.desc()).first()

        if latest_quality:
            violations = db.query(QualityViolation).filter(QualityViolation.execution_id == latest_quality.id).all()
            for v in violations:
                if v.severity in ["high", "critical"]:
                    title = f"Resolve Quality Failure in {v.column_name or 'dataset'}"
                    priority = v.severity
                    
                    # Explainability payload
                    why_generated = f"This recommendation was generated because the quality check failed."
                    evidence = f"Rule failed on column '{v.column_name}'. Actual value: {v.actual_value}. Expected threshold: {v.expected_value}."

                    
                    desc = f"Title: {title}\nWhy: {why_generated}\nEvidence: {evidence}\nMessage: {v.message}"
                    
                    rec = Recommendation(
                        dataset_version_id=dataset_version_id,
                        recommendation_type="QUALITY_REMEDIATION",
                        priority=priority,
                        title=title,
                        description=desc,
                        status="OPEN"
                    )
                    db.add(rec)
                    recommendations.append(rec)

        # 2. Inspect Anomalies
        latest_anomaly = db.query(AnomalyDetectionRun).filter(
            AnomalyDetectionRun.dataset_version_id == dataset_version_id,
            AnomalyDetectionRun.status == "completed"
        ).order_by(AnomalyDetectionRun.started_at.desc()).first()

        if latest_anomaly:
            anomalies = db.query(DetectedAnomaly).filter(DetectedAnomaly.run_id == latest_anomaly.id).all()
            if anomalies:
                # Group anomalies by column
                columns_anomalous = set(a.column_name for a in anomalies)
                for col in columns_anomalous:
                    col_anoms = [a for a in anomalies if a.column_name == col]
                    title = f"Investigate Outliers in Column {col}"
                    priority = "high" if len(col_anoms) > 5 else "medium"
                    
                    why = f"Generated due to a high density of outlier points detected in '{col}'."
                    evidence = f"Detected {len(col_anoms)} anomaly points using algorithm {latest_anomaly.algorithm}."
                    desc = f"Title: {title}\nWhy: {why}\nEvidence: {evidence}"

                    rec = Recommendation(
                        dataset_version_id=dataset_version_id,
                        recommendation_type="ANOMALY_INVESTIGATION",
                        priority=priority,
                        title=title,
                        description=desc,
                        status="OPEN"
                    )
                    db.add(rec)
                    recommendations.append(rec)

        # 3. Inspect Drift
        latest_drift = db.query(DatasetDriftRun).filter(
            DatasetDriftRun.dataset_version_id == dataset_version_id,
            DatasetDriftRun.status == "completed"
        ).order_by(DatasetDriftRun.created_at.desc()).first()

        if latest_drift:
            drift_results = db.query(ColumnDriftResult).filter(ColumnDriftResult.drift_run_id == latest_drift.id).all()
            significant = [d for d in drift_results if d.severity in ["MEDIUM", "HIGH"]]
            
            for d in significant:
                title = f"Review Drift in Column {d.column_name}"
                priority = "high" if d.severity == "HIGH" else "medium"
                
                why = f"Generated due to significant data drift detected compared to baseline."
                evidence = f"Metric '{d.drift_metric}' score is {d.drift_score:.4f} (Severity: {d.severity})."
                desc = f"Title: {title}\nWhy: {why}\nEvidence: {evidence}"

                rec = Recommendation(
                    dataset_version_id=dataset_version_id,
                    recommendation_type="DRIFT_REVIEW",
                    priority=priority,
                    title=title,
                    description=desc,
                    status="OPEN"
                )
                db.add(rec)
                recommendations.append(rec)

        db.commit()
        return recommendations
