import io
import uuid
import pytest
from src.models.dataset import Dataset, DatasetVersion
from src.models.quality import DataQualityRule
from src.models.drift import DriftBaseline
from src.models.reliability import ValidationReport, DatasetHealthHistory
from src.models.quality_execution import DataQualityExecution
from src.models.anomaly_run import AnomalyDetectionRun
from src.tasks.quality_tasks import (
    run_quality_checks,
    run_anomaly_detection,
    run_dataset_drift_detection,
    run_full_validation_pipeline
)

def test_celery_quality_checks_task(client, admin_headers, db):
    # Setup dataset
    csv_data = "col1,col2\n1,foo\n,bar\n" # 1 null
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Celery Quality Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]
    dataset_id = up_res.json()["dataset_id"]

    # Add rule
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Null check", "rule_type": "NULL_PERCENT", "threshold": 0.0}
    )

    # Run celery task synchronously
    res = run_quality_checks(version_id)
    assert "Quality validation finished" in res

    # Verify execution record exists in DB
    exec_record = db.query(DataQualityExecution).filter(
        DataQualityExecution.dataset_version_id == uuid.UUID(version_id)
    ).first()
    assert exec_record is not None
    assert exec_record.status == "completed"
    assert exec_record.summary_json["total_violations"] == 1

def test_celery_anomaly_detection_task(client, admin_headers, db):
    csv_data = "col1\n1.0\n1.1\n1.2\n1.0\n1.1\n10.0\n" # 10.0 is outlier
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Celery Anomaly Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]

    res = run_anomaly_detection(version_id, "iqr")
    assert "Anomaly detection finished" in res

    # Verify run record in DB
    run = db.query(AnomalyDetectionRun).filter(
        AnomalyDetectionRun.dataset_version_id == uuid.UUID(version_id)
    ).first()
    assert run is not None
    assert run.status == "completed"
    assert run.anomalies_found == 1

def test_full_pipeline_task(client, admin_headers, db):
    csv_base = "col1,col2\n10,foo\n10,bar\n"
    csv_target = "col1,col2\n20,foo\n20,bar\n" # mean shifted from 10 to 20

    # 1. Upload baseline
    up_base = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Reliability Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_base.encode("utf-8")), "text/csv")}
    )
    base_id = up_base.json()["id"]
    dataset_id = up_base.json()["dataset_id"]

    # Set drift baseline
    client.post(
        f"/api/v1/datasets/{dataset_id}/baseline",
        headers=admin_headers,
        params={"baseline_version_id": base_id}
    )

    # 2. Upload target version
    up_target = client.post(
        f"/api/v1/datasets/{dataset_id}/version",
        headers=admin_headers,
        files={"file": ("v2.csv", io.BytesIO(csv_target.encode("utf-8")), "text/csv")}
    )
    target_id = up_target.json()["id"]

    # 3. Add rules
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Null Limit", "rule_type": "NULL_PERCENT", "threshold": 0.0}
    )

    # Run full pipeline
    pipeline_res = run_full_validation_pipeline(target_id)
    assert "Full validation pipeline completed" in pipeline_res

    # Check ValidationReport is created
    report = db.query(ValidationReport).filter(
        ValidationReport.dataset_version_id == uuid.UUID(target_id)
    ).first()
    assert report is not None
    assert report.health_score > 0
    assert report.quality_score > 0
    assert report.anomaly_score > 0
    assert report.drift_score > 0

    # Check health history
    history = db.query(DatasetHealthHistory).filter(
        DatasetHealthHistory.dataset_version_id == uuid.UUID(target_id)
    ).first()
    assert history is not None
    assert history.health_score == report.health_score

def test_quality_endpoints(client, admin_headers):
    # Test triggering quality run via API
    response = client.post(
        f"/api/v1/datasets/versions/{uuid.uuid4()}/quality/run",
        headers=admin_headers
    )
    # Returns 404 since UUID is not in database, which verifies route is mounted and executing DB lookup
    assert response.status_code == 404

def test_anomaly_endpoints(client, admin_headers):
    response = client.post(
        f"/api/v1/anomalies/versions/{uuid.uuid4()}/run",
        headers=admin_headers
    )
    assert response.status_code == 404

def test_drift_endpoints(client, admin_headers):
    response = client.post(
        f"/api/v1/datasets/{uuid.uuid4()}/drift/run",
        headers=admin_headers,
        params={"target_version_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404

def test_analytics_endpoints(client, admin_headers):
    # Verify summary routes
    response = client.get("/api/v1/analytics/quality-summary", headers=admin_headers)
    assert response.status_code == 200
    assert "total_executions" in response.json()

    response = client.get("/api/v1/analytics/anomaly-summary", headers=admin_headers)
    assert response.status_code == 200
    assert "total_runs" in response.json()

    response = client.get("/api/v1/analytics/top-violations", headers=admin_headers)
    assert response.status_code == 200

    response = client.get("/api/v1/analytics/data-health-score", headers=admin_headers)
    assert response.status_code == 200

def test_health_endpoint_diagnostics(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "latest_quality_run_status" in data
    assert "latest_anomaly_run_status" in data

def test_analytics_dataset_history_not_found(client, admin_headers):
    response = client.get(
        f"/api/v1/analytics/datasets/{uuid.uuid4()}/history",
        headers=admin_headers
    )
    assert response.status_code == 404

def test_drift_baseline_association_mismatch(client, admin_headers):
    # Setting baseline version of a dataset that does not match dataset_id
    response = client.post(
        f"/api/v1/datasets/{uuid.uuid4()}/baseline",
        headers=admin_headers,
        params={"baseline_version_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404

def test_drift_runs_list(client, admin_headers):
    response = client.get(
        f"/api/v1/datasets/{uuid.uuid4()}/drift",
        headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_drift_baseline_set_success(client, admin_headers, db):
    # Register dataset first
    csv_data = "col1\n1\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Drift Baseline Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]
    dataset_id = up_res.json()["dataset_id"]

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/baseline",
        headers=admin_headers,
        params={"baseline_version_id": version_id}
    )
    assert response.status_code == 200
    assert response.json()["baseline_version_id"] == version_id

    # Test baseline update path (updates existing baseline)
    response_update = client.post(
        f"/api/v1/datasets/{dataset_id}/baseline",
        headers=admin_headers,
        params={"baseline_version_id": version_id}
    )
    assert response_update.status_code == 200

def test_get_drift_runs_success(client, admin_headers, db):
    # Retrieve runs for a valid dataset ID
    response = client.get(
        f"/api/v1/datasets/{uuid.uuid4()}/drift",
        headers=admin_headers
    )
    assert response.status_code == 200

def test_get_health_history_success(client, admin_headers):
    response = client.get(
        f"/api/v1/datasets/{uuid.uuid4()}/health/history",
        headers=admin_headers
    )
    assert response.status_code == 200

def test_anomalies_run_listing_and_details(client, admin_headers, db):
    ver_id = uuid.uuid4()
    # Check listing runs
    response = client.get(
        f"/api/v1/anomalies/versions/{ver_id}",
        headers=admin_headers
    )
    assert response.status_code == 200
    
    # Check details of invalid run
    response_details = client.get(
        f"/api/v1/anomalies/{uuid.uuid4()}",
        headers=admin_headers
    )
    assert response_details.status_code == 404

def test_quality_execution_listing_and_details(client, admin_headers):
    ver_id = uuid.uuid4()
    response = client.get(
        f"/api/v1/datasets/versions/{ver_id}/quality",
        headers=admin_headers
    )
    assert response.status_code == 200

    response_details = client.get(
        f"/api/v1/datasets/executions/{uuid.uuid4()}",
        headers=admin_headers
    )
    assert response_details.status_code == 404

def test_celery_quality_checks_task_failure():
    # Will fail because version ID doesn't exist
    with pytest.raises(ValueError):
        run_quality_checks(str(uuid.uuid4()))

def test_celery_anomaly_detection_task_failure():
    with pytest.raises(ValueError):
        run_anomaly_detection(str(uuid.uuid4()))

def test_celery_drift_detection_task_failure():
    with pytest.raises(ValueError):
        run_dataset_drift_detection(str(uuid.uuid4()), str(uuid.uuid4()))


