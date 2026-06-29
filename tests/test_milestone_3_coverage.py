import uuid
import io
import pytest

from datetime import datetime, timedelta
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.reliability import ValidationReport
from src.models.scorecard import ReliabilityScorecard, ExecutiveScorecard
from src.models.observability import DataIncident, IncidentComment
from src.models.quality_execution import DataQualityExecution, QualityViolation
from src.models.anomaly_run import AnomalyDetectionRun, DetectedAnomaly
from src.models.drift import DatasetDriftRun, ColumnDriftResult
from src.models.sla import DatasetSLA
from src.models.leaderboard import Leaderboard
from src.models.recommendation import Recommendation
from src.services.lineage_engine import LineageEngine
from src.services.catalog_engine import CatalogEngine
from src.services.trend_engine import TrendEngine



from src.services.freshness_engine import FreshnessEngine
from src.services.leaderboard_engine import LeaderboardEngine
from src.services.observability_engine import ObservabilityEngine
from src.services.root_cause_engine import RootCauseEngine
from src.services.recommendation_engine import RecommendationEngine
from src.services.reliability_engine import ReliabilityEngine
from src.services.executive_scorecard_engine import ExecutiveScorecardEngine
from src.services.sla_engine import SLAEngine
from src.tasks.analytics_tasks import (
    run_dataset_comparison,
    run_root_cause_analysis,
    generate_recommendations,
    generate_scorecard,
    refresh_leaderboards
)


@pytest.fixture
def test_setup_data(db):
    # Setup test owner user
    user = User(
        id=uuid.uuid4(),
        email="test_analytics_user@test.com",
        hashed_password="dummy_password",
        role="Admin"
    )
    db.add(user)
    db.commit()

    # Create 2 datasets
    ds1 = Dataset(id=uuid.uuid4(), name="Dataset Alpha", owner_id=user.id)
    ds2 = Dataset(id=uuid.uuid4(), name="Dataset Beta", owner_id=user.id)
    db.add_all([ds1, ds2])
    db.commit()

    # Create versions
    ver1 = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds1.id, version_number=1,
        file_path="p1.csv", filename="p1.csv", mime_type="text/csv",
        row_count=100, column_count=4, file_size=500
    )
    ver2 = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds2.id, version_number=1,
        file_path="p2.csv", filename="p2.csv", mime_type="text/csv",
        row_count=200, column_count=4, file_size=1000
    )
    db.add_all([ver1, ver2])
    db.commit()

    # Write physical CSV files to disk for profiling/comparison reads
    with open("p1.csv", "w") as f:
        f.write("col1,col2,col3,col4\n1,2,3,4\n5,6,7,8\n")
    with open("p2.csv", "w") as f:
        f.write("col1,col2,col3,col4\n1,2,3,4\n5,6,7,8\n")

    yield {"user": user, "ds1": ds1, "ds2": ds2, "ver1": ver1, "ver2": ver2}

    import os
    for path in ["p1.csv", "p2.csv"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def test_lineage_complex_graph(db, test_setup_data):
    ds1 = test_setup_data["ds1"]
    ds2 = test_setup_data["ds2"]
    
    # ds1 -> ds2 (dependency)
    dep = LineageEngine.add_dependency(db, ds1.id, ds2.id, "derived_from")
    assert dep is not None

    upstream = LineageEngine.get_upstream(db, ds2.id)
    assert len(upstream) == 1
    assert upstream[0]["source_dataset_id"] == ds1.id

    downstream = LineageEngine.get_downstream(db, ds1.id)
    assert len(downstream) == 1
    assert downstream[0]["target_dataset_id"] == ds2.id

    blast_radius = LineageEngine.calculate_blast_radius(db, ds1.id)
    assert blast_radius == 1

def test_freshness_engine_scenarios(db, test_setup_data):
    ds1 = test_setup_data["ds1"]
    expected = datetime.utcnow() - timedelta(hours=2) # 2 hours delay
    
    # Log late
    rec = FreshnessEngine.log_freshness(db, ds1.id, expected)
    assert rec.status == "critical"
    assert rec.delay_minutes >= 120

    metrics = FreshnessEngine.get_metrics(db, ds1.id)
    assert metrics["freshness_score"] == 0.0
    assert metrics["sla_breach"] is True

def test_leaderboard_engine_complex(db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    ver2 = test_setup_data["ver2"]

    # Ingest validation reports for rank sorting
    rep1 = ValidationReport(
        dataset_version_id=ver1.id, health_score=95.0, quality_score=90.0,
        drift_score=85.0, anomaly_score=80.0, report_json={}
    )
    rep2 = ValidationReport(
        dataset_version_id=ver2.id, health_score=60.0, quality_score=50.0,
        drift_score=70.0, anomaly_score=90.0, report_json={}
    )
    db.add_all([rep1, rep2])
    db.commit()

    # Generate scorecard for best_overall category
    sc1 = ReliabilityEngine.generate_scorecard(db, ver1.id, 95.0, 90.0, 85.0, 80.0)
    sc2 = ReliabilityEngine.generate_scorecard(db, ver2.id, 60.0, 50.0, 70.0, 90.0)

    # Refresh rankings
    lbs = LeaderboardEngine.refresh(db)
    assert len(lbs) > 0

    # Best health should rank ds1 (95.0) above ds2 (60.0)
    best_health = db.query(Leaderboard).filter(
        Leaderboard.dataset_id == test_setup_data["ds1"].id,
        Leaderboard.category == "best_health"
    ).first()
    assert best_health.rank == 1

def test_observability_engine_breaches(db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    
    # Case 1: Low health score breach
    rep = ValidationReport(
        dataset_version_id=ver1.id, health_score=40.0, quality_score=10.0,
        drift_score=10.0, anomaly_score=10.0, report_json={}
    )
    db.add(rep)
    db.commit()

    incidents = ObservabilityEngine.evaluate_and_trigger_incidents(db, ver1.id)
    assert len(incidents) >= 1
    assert any(i.severity == "critical" for i in incidents)

def test_observability_critical_quality_violations(db, test_setup_data):
    ver2 = test_setup_data["ver2"]
    
    # Case 2: Quality execution with critical severity violation
    exec_run = DataQualityExecution(dataset_version_id=ver2.id, status="completed")
    db.add(exec_run)
    db.commit()

    violation = QualityViolation(
        execution_id=exec_run.id, severity="critical", message="Critical schema mismatch error"
    )
    db.add(violation)
    db.commit()

    incidents = ObservabilityEngine.evaluate_and_trigger_incidents(db, ver2.id)
    assert len(incidents) >= 1
    assert any(i.severity == "high" for i in incidents)

def test_root_cause_analysis_generation(db, test_setup_data):
    ver1 = test_setup_data["ver1"]

    # Quality execution
    exec_run = DataQualityExecution(dataset_version_id=ver1.id, status="completed")
    db.add(exec_run)
    db.commit()

    # Create referential check breach
    v = QualityViolation(
        execution_id=exec_run.id, severity="high", column_name="user_id",
        message="Referential integrity validation check failed"
    )
    db.add(v)
    db.commit()

    rcas = RootCauseEngine.analyze(db, ver1.id)
    assert len(rcas) >= 1
    assert rcas[0].issue_type == "quality"
    assert rcas[0].root_cause_category == "referential_breaks"
    assert rcas[0].confidence_score > 0.0

def test_root_cause_anomalies_and_drift(db, test_setup_data):
    ver2 = test_setup_data["ver2"]

    # Anomaly run
    anom_run = AnomalyDetectionRun(dataset_version_id=ver2.id, algorithm="iqr", status="completed")
    db.add(anom_run)
    db.commit()

    anom = DetectedAnomaly(run_id=anom_run.id, column_name="salary", anomaly_type="IQR")
    db.add(anom)
    db.commit()

    # Drift run
    drift_run = DatasetDriftRun(dataset_version_id=ver2.id, baseline_version_id=uuid.uuid4(), status="completed")
    db.add(drift_run)
    db.commit()

    drift_res = ColumnDriftResult(drift_run_id=drift_run.id, column_name="salary", drift_metric="MEAN_SHIFT", drift_score=0.4, severity="HIGH")
    db.add(drift_res)
    db.commit()

    rcas = RootCauseEngine.analyze(db, ver2.id)
    assert len(rcas) >= 2
    types = [r.issue_type for r in rcas]
    assert "anomaly" in types
    assert "drift" in types

def test_recommendation_generation_explainability(db, test_setup_data):
    ver1 = test_setup_data["ver1"]

    # Quality
    exec_run = DataQualityExecution(dataset_version_id=ver1.id, status="completed")
    db.add(exec_run)
    db.commit()
    v = QualityViolation(execution_id=exec_run.id, severity="critical", column_name="email", message="Null checks breached")
    db.add(v)
    db.commit()

    # Anomaly
    anom_run = AnomalyDetectionRun(dataset_version_id=ver1.id, algorithm="zscore", status="completed")
    db.add(anom_run)
    db.commit()
    for _ in range(6):
        db.add(DetectedAnomaly(run_id=anom_run.id, column_name="age", anomaly_type="Z_SCORE"))
    db.commit()

    # Drift
    drift_run = DatasetDriftRun(dataset_version_id=ver1.id, baseline_version_id=uuid.uuid4(), status="completed")
    db.add(drift_run)
    db.commit()
    db.add(ColumnDriftResult(drift_run_id=drift_run.id, column_name="salary", drift_metric="PSI", drift_score=0.35, severity="HIGH"))
    db.commit()

    recs = RecommendationEngine.generate(db, ver1.id)
    assert len(recs) >= 3

    types = [r.recommendation_type for r in recs]
    assert "QUALITY_REMEDIATION" in types
    assert "ANOMALY_INVESTIGATION" in types
    assert "DRIFT_REVIEW" in types

    # Check evidence explainability is serialized in descriptions
    assert "Evidence" in recs[0].description
    assert "Why" in recs[0].description

def test_sla_engine_targets(db, test_setup_data):
    ds1 = test_setup_data["ds1"]
    
    # Create target quality score SLA limit
    sla = DatasetSLA(
        dataset_id=ds1.id,
        target_freshness_hours=1, # 1 hour expected
        target_quality_score=98.0
    )
    db.add(sla)
    db.commit()

    sla_eval = SLAEngine.check_sla(db, ds1.id)
    assert sla_eval.compliance_pct == 50.0 # Freshness target is met, but quality is not


def test_executive_scorecard_dashboard(db, test_setup_data):
    # Log open incidents
    inc = DataIncident(
        dataset_version_id=test_setup_data["ver1"].id,
        status="OPEN",
        severity="critical",
        title="Alert",
        description="Critical alert"
    )
    db.add(inc)
    db.commit()

    scorecard = ExecutiveScorecardEngine.generate(db)
    assert scorecard.critical_incidents == 1

def test_api_remediation_patches(client, admin_headers, db, test_setup_data):
    rec = Recommendation(
        dataset_version_id=test_setup_data["ver1"].id,
        recommendation_type="RULE_CREATION",
        priority="low",
        title="Add Unique check",
        description="Detail",
        status="OPEN"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    response = client.patch(
        f"/api/v1/recommendations/{rec.id}?status=applied",
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPLIED"

def test_api_incident_comment_and_assignment(client, admin_headers, db, test_setup_data):
    inc = DataIncident(
        dataset_version_id=test_setup_data["ver1"].id,
        status="OPEN",
        severity="medium",
        title="Alert",
        description="Detail"
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    # Assign
    response = client.post(
        f"/api/v1/incidents/{inc.id}/assign?user_id={test_setup_data['user'].id}",
        headers=admin_headers
    )
    assert response.status_code == 200

    # Comment
    response = client.post(
        f"/api/v1/incidents/{inc.id}/comments?comment=investigating",
        headers=admin_headers
    )
    assert response.status_code == 201

def test_semantic_catalog_pii_types(client, admin_headers, db):
    # Test all semantic category matching
    csv_data = "phone_num,first_name,street_address,ip,revenue_amount,postal_code,update_time\n+123,Alice,Main St,127.0.0.1,100,90210,2026-06-29\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Catalog PII Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    v_id = up_res.json()["id"]
    catalog = CatalogEngine.profile_semantic_metadata(db, uuid.UUID(v_id))
    # Profile again to test branch deleting existing column metadata
    catalog2 = CatalogEngine.profile_semantic_metadata(db, uuid.UUID(v_id))
    assert catalog.sensitivity_level == "CONFIDENTIAL"

    # Test nonexistent version error path
    with pytest.raises(ValueError, match="Dataset version not found"):
        CatalogEngine.profile_semantic_metadata(db, uuid.uuid4())


def test_trend_forecasting_empty_and_single():
    assert TrendEngine.calculate_linear_regression_forecast([]) == 100.0
    assert TrendEngine.calculate_linear_regression_forecast([90.0]) == 90.0
    assert TrendEngine.calculate_moving_average_forecast([]) == 100.0

def test_api_comparisons_endpoints(client, admin_headers, db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    ver2 = test_setup_data["ver2"]
    
    # 1. Trigger comparison
    response = client.post(
        f"/api/v1/comparisons/run?source_version_id={ver1.id}&target_version_id={ver2.id}",
        headers=admin_headers
    )
    assert response.status_code == 202

    # 2. List comparisons
    response_list = client.get("/api/v1/comparisons", headers=admin_headers)
    assert response_list.status_code == 200

def test_api_root_cause_endpoints(client, admin_headers, db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    
    # 1. Trigger
    response = client.post(
        f"/api/v1/root-cause/run?dataset_version_id={ver1.id}",
        headers=admin_headers
    )
    assert response.status_code == 202

    # 2. List
    response_list = client.get("/api/v1/root-cause", headers=admin_headers)
    assert response_list.status_code == 200

def test_api_recommendation_endpoints(client, admin_headers, db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    
    # List
    response = client.get("/api/v1/recommendations", headers=admin_headers)
    assert response.status_code == 200

def test_api_reliability_endpoints(client, admin_headers, db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    
    # History
    response = client.get("/api/v1/reliability/history", headers=admin_headers)
    assert response.status_code == 200

def test_api_analytics_dashboard_endpoints(client, admin_headers, db, test_setup_data):
    ds1 = test_setup_data["ds1"]
    
    # Trends
    response = client.get("/api/v1/analytics/trends", headers=admin_headers)
    assert response.status_code == 200

    # Forecast
    response = client.get(f"/api/v1/analytics/trends/forecast?dataset_id={ds1.id}", headers=admin_headers)
    assert response.status_code == 200

    # Top risks
    response = client.get("/api/v1/analytics/top-issues", headers=admin_headers)
    assert response.status_code == 200

    # Improvements
    response = client.get("/api/v1/analytics/improvements", headers=admin_headers)
    assert response.status_code == 200

def test_celery_analytics_tasks_execution(db, test_setup_data):
    ver1 = test_setup_data["ver1"]
    ver2 = test_setup_data["ver2"]
    
    res1 = run_dataset_comparison(str(ver1.id), str(ver2.id))
    assert "completed" in res1

    res2 = run_root_cause_analysis(str(ver1.id))
    assert "finished" in res2

    res3 = generate_recommendations(str(ver1.id))
    assert "Generated" in res3

    res4 = generate_scorecard(str(ver1.id), 90.0, 90.0, 90.0, 90.0)
    assert "generated" in res4

    res5 = refresh_leaderboards()
    assert "updated" in res5

