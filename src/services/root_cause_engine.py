import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.models.root_cause import RootCauseAnalysis
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.drift import DatasetDriftRun, ColumnDriftResult
from src.models.dataset import DatasetVersion

class RootCauseEngine:
    @staticmethod
    def analyze(
        db: Session,
        dataset_version_id: uuid.UUID,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> List[RootCauseAnalysis]:
        """
        Analyzes validation outputs (quality, anomalies, drift) for the version.
        Calculates confidence score: (affected_cols / total_cols)*0.5 + (severity_weight / 4.0)*0.5.
        Saves and returns list of RootCauseAnalysis records.
        """
        analyses = []
        version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not version:
            return analyses

        total_cols = version.column_count or 1
        if total_cols == 0:
            total_cols = 1

        # 1. Quality failures analysis
        latest_quality = db.query(DataQualityExecution).filter(
            DataQualityExecution.dataset_version_id == dataset_version_id,
            DataQualityExecution.status == "completed"
        ).order_by(DataQualityExecution.started_at.desc()).first()

        if latest_quality:
            violations = db.query(QualityViolation).filter(QualityViolation.execution_id == latest_quality.id).all()
            if violations:
                affected_cols = len(set(v.column_name for v in violations if v.column_name))
                severity_map = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}
                max_sev = max(severity_map.get(v.severity, 1.0) for v in violations)

                confidence = (affected_cols / total_cols) * 0.5 + (max_sev / 4.0) * 0.5
                confidence = float(min(confidence, 1.0))

                # Classify categories
                categories = []
                for v in violations:
                    v_msg = v.message.upper()
                    if "NULL" in v_msg or "MISSING" in v_msg:
                        categories.append("missing_data")
                    elif "DUPLICATE" in v_msg:
                        categories.append("duplicate_records")
                    elif "REGEX" in v_msg or "FORMAT" in v_msg:
                        categories.append("schema_violations")
                    elif "MIN" in v_msg or "MAX" in v_msg:
                        categories.append("range_failures")
                    elif "REFERENTIAL" in v_msg:
                        categories.append("referential_breaks")
                    else:
                        categories.append("schema_violations")

                primary_category = max(set(categories), key=categories.count) if categories else "schema_violations"

                rca = RootCauseAnalysis(
                    dataset_version_id=dataset_version_id,
                    issue_type="quality",
                    root_cause_category=primary_category,
                    confidence_score=confidence,
                    analysis_json={
                        "total_violations": len(violations),
                        "affected_columns": list(set(v.column_name for v in violations if v.column_name)),
                        "max_severity": max(v.severity for v in violations)
                    },
                    trace_id=trace_id,
                    span_id=span_id
                )
                db.add(rca)
                analyses.append(rca)

        # 2. Anomalies analysis
        latest_anomaly = db.query(AnomalyDetectionRun).filter(
            AnomalyDetectionRun.dataset_version_id == dataset_version_id,
            AnomalyDetectionRun.status == "completed"
        ).order_by(AnomalyDetectionRun.started_at.desc()).first()

        if latest_anomaly:
            anomalies = db.query(DetectedAnomaly).filter(DetectedAnomaly.run_id == latest_anomaly.id).all()
            if anomalies:
                affected_cols = len(set(a.column_name for a in anomalies if a.column_name))
                confidence = (affected_cols / total_cols) * 0.5 + 0.5 # Default to high severity weight of 4/4
                confidence = float(min(confidence, 1.0))

                types = [a.anomaly_type.lower() for a in anomalies]
                primary_type = "single_column_outlier"
                if "isolation_forest" in types:
                    primary_type = "multivariate_outlier"
                elif "local_outlier_factor" in types:
                    primary_type = "density_outlier"

                rca = RootCauseAnalysis(
                    dataset_version_id=dataset_version_id,
                    issue_type="anomaly",
                    root_cause_category=primary_type,
                    confidence_score=confidence,
                    analysis_json={
                        "total_anomalies": len(anomalies),
                        "affected_columns": list(set(a.column_name for a in anomalies if a.column_name))
                    },
                    trace_id=trace_id,
                    span_id=span_id
                )
                db.add(rca)
                analyses.append(rca)

        # 3. Drift analysis
        latest_drift = db.query(DatasetDriftRun).filter(
            DatasetDriftRun.dataset_version_id == dataset_version_id,
            DatasetDriftRun.status == "completed"
        ).order_by(DatasetDriftRun.created_at.desc()).first()

        if latest_drift:
            drift_results = db.query(ColumnDriftResult).filter(ColumnDriftResult.drift_run_id == latest_drift.id).all()
            significant_drift = [d for d in drift_results if d.severity in ["MEDIUM", "HIGH"]]
            if significant_drift:
                affected_cols = len(set(d.column_name for d in significant_drift))
                severity_map = {"LOW": 1.0, "MEDIUM": 2.5, "HIGH": 4.0}
                max_sev = max(severity_map.get(d.severity, 1.0) for d in significant_drift)

                confidence = (affected_cols / total_cols) * 0.5 + (max_sev / 4.0) * 0.5
                confidence = float(min(confidence, 1.0))

                categories = []
                for d in significant_drift:
                    if d.drift_metric == "PSI" or d.drift_metric == "DIST_DRIFT":
                        categories.append("distribution_shift")
                    elif d.drift_metric == "MEAN_SHIFT":
                        categories.append("mean_shift")
                    elif d.drift_metric == "STD_SHIFT":
                        categories.append("variance_shift")
                    elif d.drift_metric == "CARD_DRIFT":
                        categories.append("cardinality_shift")

                primary_category = max(set(categories), key=categories.count) if categories else "distribution_shift"

                rca = RootCauseAnalysis(
                    dataset_version_id=dataset_version_id,
                    issue_type="drift",
                    root_cause_category=primary_category,
                    confidence_score=confidence,
                    analysis_json={
                        "overall_drift_score": latest_drift.overall_drift_score,
                        "affected_columns": list(set(d.column_name for d in significant_drift))
                    },
                    trace_id=trace_id,
                    span_id=span_id
                )
                db.add(rca)
                analyses.append(rca)

        db.commit()
        return analyses
