import io
import uuid
import pytest
from src.services.schema_intelligence import SchemaIntelligence
from src.services.catalog_engine import CatalogEngine
from src.services.sla_engine import SLAEngine
from src.services.trend_engine import TrendEngine
from src.services.observability_engine import ObservabilityEngine
from src.services.executive_scorecard_engine import ExecutiveScorecardEngine
from src.tasks.analytics_tasks import run_full_analytics_pipeline
from src.models.schema_evolution import SchemaVersion
from src.models.catalog import DatasetCatalog

def test_schema_evolution(client, admin_headers, db):
    # Upload v1
    csv_v1 = "id,name\n1,foo\n2,bar\n"
    up_v1 = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Schema Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_v1.encode("utf-8")), "text/csv")}
    )
    v1_id = up_v1.json()["id"]
    dataset_id = up_v1.json()["dataset_id"]

    # Ingest v1 schema
    schema_v1 = SchemaIntelligence.analyze_and_persist(db, uuid.UUID(v1_id))
    assert schema_v1 is not None

    # Upload v2 (removed 'name', added 'age', modified 'id' type by naming it to id_val)
    csv_v2 = "id_val,age\n1,30\n2,40\n"
    up_v2 = client.post(
        f"/api/v1/datasets/{dataset_id}/version",
        headers=admin_headers,
        files={"file": ("v2.csv", io.BytesIO(csv_v2.encode("utf-8")), "text/csv")}
    )
    v2_id = up_v2.json()["id"]

    # Ingest v2 schema
    schema_v2 = SchemaIntelligence.analyze_and_persist(db, uuid.UUID(v2_id))
    assert schema_v2 is not None
    assert len(schema_v2.changes) == 4


def test_semantic_catalog(client, admin_headers, db):
    # Upload data with email, phone, name, and revenue
    csv_data = "user_id,email,salary,country\n1,test@test.com,50000,US\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Catalog Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    v_id = up_res.json()["id"]

    catalog = CatalogEngine.profile_semantic_metadata(db, uuid.UUID(v_id))
    assert catalog.sensitivity_level == "CONFIDENTIAL"
    assert len(catalog.columns) == 4

    col_types = {c.column_name: c.inferred_semantic_type for c in catalog.columns}
    assert col_types["email"] == "PII"
    assert col_types["salary"] == "FINANCIAL"
    assert col_types["country"] == "GEOGRAPHY"

def test_sla_compliance(client, admin_headers, db):
    csv_data = "col1\n1\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "SLA Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    dataset_id = up_res.json()["dataset_id"]

    sla = SLAEngine.check_sla(db, uuid.UUID(dataset_id))
    assert sla.compliance_pct >= 0.0

def test_trend_forecasting():
    y = [100.0, 90.0, 80.0]
    forecast_lr = TrendEngine.calculate_linear_regression_forecast(y)
    # Series decreasing by 10 points per step. Forecast for next step (index 3) is 70.0
    assert forecast_lr == 70.0

    forecast_ma = TrendEngine.calculate_moving_average_forecast(y, window=2)
    # Average of last 2: (90.0 + 80.0) / 2 = 85.0
    assert forecast_ma == 85.0

def test_observability_incident_generation(db):
    incidents = ObservabilityEngine.evaluate_and_trigger_incidents(db, uuid.uuid4())
    assert len(incidents) == 0

def test_executive_scorecard(db):
    sc = ExecutiveScorecardEngine.generate(db)
    assert sc.overall_platform_score >= 0.0
    assert sc.sla_compliance >= 0.0

def test_api_routes(client, admin_headers):
    # Incident endpoints
    response = client.get("/api/v1/incidents", headers=admin_headers)
    assert response.status_code == 200

    response = client.get(f"/api/v1/incidents/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 404

    # SLA endpoints
    response = client.get("/api/v1/sla", headers=admin_headers)
    assert response.status_code == 200

    response = client.get(f"/api/v1/sla/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 404

    # Leaderboard endpoints
    response = client.get("/api/v1/leaderboards", headers=admin_headers)
    assert response.status_code == 200

    response = client.get("/api/v1/leaderboards/history", headers=admin_headers)
    assert response.status_code == 200

    # Executive Overview
    response = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert response.status_code == 200

def test_full_analytics_pipeline_task(client, admin_headers, db):
    csv_data = "user_id,email,salary\n1,t@t.com,500\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Pipeline Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    v_id = up_res.json()["id"]

    res = run_full_analytics_pipeline(v_id)
    assert "pipeline completed" in res

def test_lineage_dependency_and_freshness_apis(client, admin_headers):
    # Log freshness check
    fresh_payload = {
        "dataset_id": str(uuid.uuid4()),
        "expected_refresh_time": "2026-06-29T00:00:00"
    }
    response = client.post(
        "/api/v1/freshness/log",
        headers=admin_headers,
        params=fresh_payload
    )
    assert response.status_code == 201

    # Fetch freshness list
    response = client.get("/api/v1/freshness", headers=admin_headers)
    assert response.status_code == 200

    # Fetch specific freshness
    response = client.get(f"/api/v1/freshness/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 200

    # Lineage registration and traversal
    lineage_payload = {
        "source_dataset_id": str(uuid.uuid4()),
        "target_dataset_id": str(uuid.uuid4()),
        "relationship_type": "derived_from"
    }
    response = client.post(
        "/api/v1/lineage/dependency",
        headers=admin_headers,
        params=lineage_payload
    )
    assert response.status_code == 201

    # Traversal check
    response = client.get(f"/api/v1/lineage/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 200

