import uuid
from typing import Optional
from src.celery_app import celery_app
from src.database import SessionLocal
from src.services.comparison_engine import ComparisonEngine
from src.services.root_cause_engine import RootCauseEngine
from src.services.recommendation_engine import RecommendationEngine
from src.services.reliability_engine import ReliabilityEngine
from src.services.leaderboard_engine import LeaderboardEngine
from src.services.catalog_engine import CatalogEngine
from src.services.schema_intelligence import SchemaIntelligence
from src.services.observability_engine import ObservabilityEngine
from src.services.sla_engine import SLAEngine
from src.services.executive_scorecard_engine import ExecutiveScorecardEngine
from src.models.reliability import ValidationReport
from src.models.dataset import DatasetVersion

@celery_app.task(name="src.tasks.analytics_tasks.run_dataset_comparison")
def run_dataset_comparison(source_version_id: str, target_version_id: str):
    db = SessionLocal()
    try:
        source_uuid = uuid.UUID(source_version_id)
        target_uuid = uuid.UUID(target_version_id)
        comparison = ComparisonEngine.compare_versions(db, source_uuid, target_uuid)
        return f"Comparison {comparison.id} completed between {source_version_id} and {target_version_id}"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@celery_app.task(name="src.tasks.analytics_tasks.run_root_cause_analysis")
def run_root_cause_analysis(version_id: str, trace_id: Optional[str] = None, span_id: Optional[str] = None):
    db = SessionLocal()
    try:
        ver_uuid = uuid.UUID(version_id)
        rcas = RootCauseEngine.analyze(db, ver_uuid, trace_id, span_id)
        return f"Root cause analysis finished with {len(rcas)} reports for version {version_id}"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@celery_app.task(name="src.tasks.analytics_tasks.generate_recommendations")
def generate_recommendations(version_id: str):
    db = SessionLocal()
    try:
        ver_uuid = uuid.UUID(version_id)
        recs = RecommendationEngine.generate(db, ver_uuid)
        return f"Generated {len(recs)} recommendations for version {version_id}"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@celery_app.task(name="src.tasks.analytics_tasks.generate_scorecard")
def generate_scorecard(
    version_id: str,
    health_score: float,
    quality_score: float,
    drift_score: float,
    anomaly_score: float,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None
):
    db = SessionLocal()
    try:
        ver_uuid = uuid.UUID(version_id)
        scorecard = ReliabilityEngine.generate_scorecard(
            db, ver_uuid, health_score, quality_score, drift_score, anomaly_score, trace_id, span_id
        )
        return f"Scorecard {scorecard.id} generated. Reliability: {scorecard.reliability_score:.2f}"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@celery_app.task(name="src.tasks.analytics_tasks.refresh_leaderboards")
def refresh_leaderboards():
    db = SessionLocal()
    try:
        records = LeaderboardEngine.refresh(db)
        return f"Leaderboard updated. Total active categories registered: {len(records)}"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@celery_app.task(name="src.tasks.analytics_tasks.run_full_analytics_pipeline")
def run_full_analytics_pipeline(
    version_id: str,
    baseline_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None
):
    """
    Assembles the complete executive analytics flow:
    Schema Intelligence ➔ Catalog ➔ Comparison ➔ RCA ➔ Recommendations ➔ Scorecard ➔ Incidents ➔ SLA ➔ Leaderboard
    """
    db = SessionLocal()
    try:
        ver_uuid = uuid.UUID(version_id)
        version = db.query(DatasetVersion).filter(DatasetVersion.id == ver_uuid).first()
        if not version:
            raise ValueError(f"Dataset version {version_id} not found")

        # 1. Schema intelligence
        SchemaIntelligence.analyze_and_persist(db, ver_uuid)

        # 2. Semantic catalog profiling
        CatalogEngine.profile_semantic_metadata(db, ver_uuid)

        # 3. Version comparison if baseline exists
        if baseline_id:
            try:
                base_uuid = uuid.UUID(baseline_id)
                ComparisonEngine.compare_versions(db, base_uuid, ver_uuid)
            except Exception:
                pass

        # 4. Root Cause Analysis
        RootCauseEngine.analyze(db, ver_uuid, trace_id, span_id)

        # 5. Recommendation Engine
        RecommendationEngine.generate(db, ver_uuid)

        # 6. Generate Reliability Scorecard
        report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == ver_uuid).first()
        if report:
            ReliabilityEngine.generate_scorecard(
                db=db,
                dataset_version_id=ver_uuid,
                health_score=report.health_score,
                quality_score=report.quality_score,
                drift_score=report.drift_score,
                anomaly_score=report.anomaly_score,
                trace_id=trace_id,
                span_id=span_id
            )

        # 7. Evaluate incidents
        ObservabilityEngine.evaluate_and_trigger_incidents(db, ver_uuid)

        # 8. SLA calculations
        SLAEngine.check_sla(db, version.dataset_id)

        # 9. Refresh leaderboards
        LeaderboardEngine.refresh(db)

        # 10. Generate Executive Scorecard
        ExecutiveScorecardEngine.generate(db)

        return "Full analytics pipeline completed successfully"
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
