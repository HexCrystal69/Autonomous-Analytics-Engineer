import uuid
from datetime import datetime
from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.dataset import DatasetVersion, Dataset
from src.models.quality import DataQualityRule
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.drift import DatasetDriftRun, ColumnDriftResult, DriftBaseline
from src.models.reliability import ValidationReport, DatasetHealthHistory
from src.models.profile import DatasetProfile
from src.services.profiling import ProfilingEngine
from src.services.quality_engine import QualityEngine
from src.services.anomaly_engine import AnomalyEngine
from src.services.drift_engine import DriftEngine
from src.services.health_engine import HealthEngine
from src.utils.audit import log_audit

@celery_app.task
def run_quality_checks(dataset_version_id: str) -> str:
    """Task to run quality rule validations against a dataset version."""
    db = SessionLocal()
    ver_id = uuid.UUID(dataset_version_id)
    try:
        # Create execution record
        exec_record = DataQualityExecution(dataset_version_id=ver_id, status="running", started_at=datetime.utcnow())
        db.add(exec_record)
        db.commit()
        db.refresh(exec_record)

        log_audit(db, "quality_run_started", "data_quality_execution", exec_record.id)

        version = db.query(DatasetVersion).filter(DatasetVersion.id == ver_id).first()
        if not version:
            raise ValueError(f"Version {dataset_version_id} not found")

        df = ProfilingEngine.load_dataset(version.file_path, version.mime_type)
        rules = db.query(DataQualityRule).filter(DataQualityRule.dataset_id == version.dataset_id).all()

        violations = QualityEngine.validate(df, rules, db=db)

        # Write violations
        for v in violations:
            violation = QualityViolation(
                execution_id=exec_record.id,
                rule_id=v["rule_id"],
                severity=v["severity"],
                column_name=v["column_name"],
                actual_value=v["actual_value"],
                expected_value=v["expected_value"],
                message=v["message"]
            )
            db.add(violation)
            db.commit()
            db.refresh(violation)
            log_audit(db, "quality_violation_created", "quality_violation", violation.id)

        exec_record.status = "completed"
        exec_record.completed_at = datetime.utcnow()
        exec_record.summary_json = {
            "total_rules_checked": len(rules),
            "total_violations": len(violations)
        }
        db.commit()

        log_audit(db, "quality_run_completed", "data_quality_execution", exec_record.id)
        return f"Quality validation finished for version {dataset_version_id}. Violations found: {len(violations)}"
    except Exception as e:
        db.rollback()
        # Find if execution was created
        exec_record = db.query(DataQualityExecution).filter(
            DataQualityExecution.dataset_version_id == ver_id,
            DataQualityExecution.status == "running"
        ).first()
        if exec_record:
            exec_record.status = "failed"
            exec_record.completed_at = datetime.utcnow()
            exec_record.summary_json = {"error": str(e)}
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task
def run_anomaly_detection(dataset_version_id: str, algorithm: str = "iqr") -> str:
    """Task to run statistical or ML anomaly detection against a dataset version."""
    db = SessionLocal()
    ver_id = uuid.UUID(dataset_version_id)
    try:
        run = AnomalyDetectionRun(dataset_version_id=ver_id, algorithm=algorithm, status="running", started_at=datetime.utcnow())
        db.add(run)
        db.commit()
        db.refresh(run)

        log_audit(db, "anomaly_detection_started", "anomaly_detection_run", run.id)

        version = db.query(DatasetVersion).filter(DatasetVersion.id == ver_id).first()
        if not version:
            raise ValueError(f"Version {dataset_version_id} not found")

        df = ProfilingEngine.load_dataset(version.file_path, version.mime_type)
        
        # Execute selected algorithm
        alg_lower = algorithm.lower()
        if alg_lower == "zscore":
            anomalies = AnomalyEngine.detect_zscore(df)
        elif alg_lower == "isolation_forest":
            anomalies = AnomalyEngine.detect_isolation_forest(df)
        elif alg_lower == "local_outlier_factor":
            anomalies = AnomalyEngine.detect_local_outlier_factor(df)
        else:
            anomalies = AnomalyEngine.detect_iqr(df)

        for a in anomalies:
            anomaly = DetectedAnomaly(
                run_id=run.id,
                column_name=a["column_name"],
                row_index=a["row_index"],
                score=a["score"],
                anomaly_type=a["anomaly_type"],
                details_json=a["details_json"]
            )
            db.add(anomaly)

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.anomalies_found = len(anomalies)
        db.commit()

        log_audit(db, "anomaly_detection_completed", "anomaly_detection_run", run.id)
        return f"Anomaly detection finished for version {dataset_version_id}. Anomalies found: {len(anomalies)}"
    except Exception as e:
        db.rollback()
        run = db.query(AnomalyDetectionRun).filter(
            AnomalyDetectionRun.dataset_version_id == ver_id,
            AnomalyDetectionRun.status == "running"
        ).first()
        if run:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task
def run_dataset_drift_detection(dataset_version_id: str, baseline_version_id: str) -> str:
    """Task to run data drift analysis between target version and baseline version."""
    db = SessionLocal()
    ver_id = uuid.UUID(dataset_version_id)
    base_id = uuid.UUID(baseline_version_id)
    try:
        drift_run = DatasetDriftRun(dataset_version_id=ver_id, baseline_version_id=base_id, status="running")
        db.add(drift_run)
        db.commit()
        db.refresh(drift_run)

        version = db.query(DatasetVersion).filter(DatasetVersion.id == ver_id).first()
        baseline = db.query(DatasetVersion).filter(DatasetVersion.id == base_id).first()
        if not version or not baseline:
            raise ValueError("Target or baseline version not found")

        df_target = ProfilingEngine.load_dataset(version.file_path, version.mime_type)
        df_baseline = ProfilingEngine.load_dataset(baseline.file_path, baseline.mime_type)

        drift_data = DriftEngine.calculate_drift(df_baseline, df_target)

        drift_run.overall_drift_score = drift_data["overall_drift_score"]
        drift_run.status = "completed"

        for res in drift_data["results"]:
            col_res = ColumnDriftResult(
                drift_run_id=drift_run.id,
                column_name=res["column_name"],
                drift_metric=res["drift_metric"],
                drift_score=res["drift_score"],
                severity=res["severity"]
            )
            db.add(col_res)

        db.commit()
        return f"Drift detection finished. Overall drift: {drift_run.overall_drift_score:.4f}"
    except Exception as e:
        db.rollback()
        drift_run = db.query(DatasetDriftRun).filter(
            DatasetDriftRun.dataset_version_id == ver_id,
            DatasetDriftRun.status == "running"
        ).first()
        if drift_run:
            drift_run.status = "failed"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task
def run_full_validation_pipeline(dataset_version_id: str) -> str:
    """Orchestrated pipeline running profiling, quality, anomaly, drift, and health scoring."""
    db = SessionLocal()
    ver_id = uuid.UUID(dataset_version_id)
    try:
        version = db.query(DatasetVersion).filter(DatasetVersion.id == ver_id).first()
        if not version:
            raise ValueError(f"Version {dataset_version_id} not found")

        # 1. Profile Generation (if missing)
        profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == ver_id).first()
        if not profile:
            profile_data = ProfilingEngine.profile(version.file_path, version.mime_type)
            profile = DatasetProfile(
                dataset_version_id=ver_id,
                summary_metrics=profile_data["summary_metrics"],
                columns_metadata=profile_data["columns_metadata"]
            )
            db.add(profile)
            version.row_count = profile_data["summary_metrics"]["row_count"]
            version.column_count = profile_data["summary_metrics"]["column_count"]
            db.commit()

        # 2. Run Quality Checks (Synchronous helper run)
        run_quality_checks.run(dataset_version_id)

        # 3. Run Anomaly Checks (Default to IQR)
        run_anomaly_detection.run(dataset_version_id, "iqr")

        # 4. Drift Check (if baseline defined)
        baseline = db.query(DriftBaseline).filter(DriftBaseline.dataset_id == version.dataset_id).first()
        if baseline:
            run_dataset_drift_detection.run(dataset_version_id, str(baseline.baseline_version_id))

        # Retrieve completed stats
        latest_exec = db.query(DataQualityExecution).filter(
            DataQualityExecution.dataset_version_id == ver_id,
            DataQualityExecution.status == "completed"
        ).order_by(DataQualityExecution.started_at.desc()).first()

        latest_anomaly = db.query(AnomalyDetectionRun).filter(
            AnomalyDetectionRun.dataset_version_id == ver_id,
            AnomalyDetectionRun.status == "completed"
        ).order_by(AnomalyDetectionRun.started_at.desc()).first()

        latest_drift = db.query(DatasetDriftRun).filter(
            DatasetDriftRun.dataset_version_id == ver_id,
            DatasetDriftRun.status == "completed"
        ).order_by(DatasetDriftRun.created_at.desc()).first()

        num_violations = latest_exec.summary_json.get("total_violations", 0) if latest_exec else 0
        num_anomalies = latest_anomaly.anomalies_found if latest_anomaly else 0

        null_percent = profile.summary_metrics.get("missing_cells_percent", 0.0)
        dup_percent = profile.summary_metrics.get("duplicate_rows_percent", 0.0)

        # 5. Compute Health Scores
        health_details = HealthEngine.calculate_health_score(
            null_percent=null_percent,
            duplicate_percent=dup_percent,
            num_violations=num_violations,
            num_anomalies=num_anomalies
        )

        overall_drift = latest_drift.overall_drift_score if latest_drift else 0.0
        # Drift score is 100 - (drift_score * 100) capped
        drift_score = float(max(0.0, 100.0 - (overall_drift * 100.0)))

        # 6. Save validation report
        report = ValidationReport(
            dataset_version_id=ver_id,
            quality_execution_id=latest_exec.id if latest_exec else None,
            anomaly_run_id=latest_anomaly.id if latest_anomaly else None,
            health_score=health_details["health_score"],
            quality_score=health_details["quality_score"],
            anomaly_score=health_details["anomaly_score"],
            drift_score=drift_score,
            report_json={
                "health_status": health_details["status"],
                "penalties": health_details["breakdown"],
                "overall_drift": overall_drift
            }
        )
        db.add(report)

        # 7. Add health history
        history = DatasetHealthHistory(
            dataset_version_id=ver_id,
            health_score=health_details["health_score"],
            quality_score=health_details["quality_score"],
            anomaly_score=health_details["anomaly_score"]
        )
        db.add(history)
        db.commit()

        # Log audit: health score calculated
        log_audit(
            db=db,
            action="health_score_calculated",
            target_type="dataset_version",
            target_id=ver_id,
            metadata_json={"health_score": health_details["health_score"]}
        )

        return f"Full validation pipeline completed for version {dataset_version_id}. Health Score: {health_details['health_score']}"
    finally:
        db.close()
