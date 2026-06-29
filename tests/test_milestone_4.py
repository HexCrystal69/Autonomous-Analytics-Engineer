import uuid
import io
import json
import pytest
from datetime import datetime, timedelta
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.reliability import ValidationReport
from src.models.sla import DatasetSLA
from src.models.observability import DataIncident
from src.models.freshness import DatasetFreshnessRecord
from src.models.contract import DataContract, DataContractRule, ContractVersion, ContractViolation
from src.models.certification import DatasetCertification
from src.models.impact import ImpactAnalysis
from src.models.monitoring import MonitoringRule, MonitoringAlert
from src.models.remediation import RemediationAction
from src.models.governance import GovernancePolicy, DatasetPolicyMapping, ComplianceSnapshot
from src.models.dashboard import ReliabilityDashboardSnapshot

from src.services.contract_engine import ContractEngine
from src.services.certification_engine import CertificationEngine
from src.services.impact_engine import ImpactEngine
from src.services.monitoring_engine import MonitoringEngine
from src.services.remediation_engine import RemediationEngine
from src.services.governance_engine import GovernanceEngine
from src.services.command_center_engine import CommandCenterEngine
from src.services.lineage_engine import LineageEngine

from src.tasks.monitoring_tasks import run_monitoring
from src.tasks.governance_tasks import evaluate_contracts
from src.tasks.impact_tasks import execute_remediation, calculate_platform_reliability

@pytest.fixture
def m4_setup_data(db):
    # Setup owner user
    user = User(
        id=uuid.uuid4(),
        email="m4_operator@dataops.com",
        hashed_password="dummy_password",
        role="Admin"
    )
    db.add(user)
    db.commit()

    # Create dataset
    ds = Dataset(id=uuid.uuid4(), name="Ops Dataset Alpha", owner_id=user.id)
    db.add(ds)
    db.commit()

    # Create CSV file physically for parsing
    with open("ops_data.csv", "w") as f:
        f.write("id,email,age,salary\n1,alice@mail.com,25,5000\n2,bob@mail.com,30,6000\n")

    # Create version
    ver = DatasetVersion(
        id=uuid.uuid4(), dataset_id=ds.id, version_number=1,
        file_path="ops_data.csv", filename="ops_data.csv", mime_type="text/csv",
        row_count=2, column_count=4, file_size=100
    )
    db.add(ver)
    db.commit()

    yield {"user": user, "ds": ds, "ver": ver}

    import os
    if os.path.exists("ops_data.csv"):
        try:
            os.remove("ops_data.csv")
        except Exception:
            pass

def test_contract_creation_and_version(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    rules = [
        {"rule_type": "column_exists", "column_name": "id", "expected_value": "", "severity": "high"},
        {"rule_type": "max_null_pct", "column_name": "email", "expected_value": "10.0", "severity": "critical"}
    ]
    contract = ContractEngine.create_contract(db, ds.id, "Alpha Contract", "Owner A", "Schema specs", "1.0.0", rules)
    assert contract.status == "active"
    assert len(contract.rules) == 2

    # Add contract version
    c_ver = ContractEngine.add_version(db, contract.id, "1.0.0", ["id", "email", "age", "salary"])
    assert c_ver.version == "1.0.0"
    assert c_ver.schema_hash is not None

def test_contract_validations_uniqueness_and_column_exists(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]

    rules = [
        {"rule_type": "column_exists", "column_name": "non_existent_column", "expected_value": "", "severity": "critical"},
        {"rule_type": "uniqueness", "column_name": "id", "expected_value": "90.0", "severity": "medium"}
    ]
    ContractEngine.create_contract(db, ds.id, "Validation Contract", "Owner B", None, "1.0.0", rules)

    violations = ContractEngine.validate_version(db, ver.id)
    assert len(violations) == 1
    assert "missing" in violations[0].message
    assert violations[0].severity == "critical"

def test_contract_validations_regex_and_range(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]

    rules = [
        {"rule_type": "regex", "column_name": "email", "expected_value": r"[a-zA-Z0-9]+@mail\.com", "severity": "high"},
        {"rule_type": "range", "column_name": "age", "expected_value": json.dumps({"min": 18, "max": 65}), "severity": "low"}
    ]
    ContractEngine.create_contract(db, ds.id, "Type Contract", "Owner C", None, "1.0.0", rules)

    violations = ContractEngine.validate_version(db, ver.id)
    assert len(violations) == 0

def test_contract_rule_failures(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]

    # Ingest catalog column metadata for column_type failure
    from src.models.catalog import DatasetCatalog, ColumnCatalog
    cat = DatasetCatalog(dataset_id=ds.id, data_owner="Admin", sensitivity_level="PUBLIC")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    col = ColumnCatalog(dataset_catalog_id=cat.id, column_name="age", semantic_type="TEMPORAL")


    db.add(col)
    db.commit()

    rules = [
        {"rule_type": "column_type", "column_name": "age", "expected_value": "PII", "severity": "high"},
        {"rule_type": "max_null_pct", "column_name": "email", "expected_value": "-1.0", "severity": "medium"},
        {"rule_type": "regex", "column_name": "email", "expected_value": r"^\d+$", "severity": "high"}, # expects all digits, which fails
        {"rule_type": "range", "column_name": "age", "expected_value": json.dumps({"min": 40, "max": 80}), "severity": "low"} # actual is 25/30, which fails min

    ]
    ContractEngine.create_contract(db, ds.id, "Failure Contract", "Owner D", None, "1.0.0", rules)

    violations = ContractEngine.validate_version(db, ver.id)
    assert len(violations) == 4


def test_dataset_certification_tiers(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]

    # Ingest validation report
    rep = ValidationReport(
        dataset_version_id=ver.id, health_score=95.0, quality_score=95.0,
        drift_score=0.1, anomaly_score=0.0, report_json={}
    )
    db.add(rep)
    db.commit()

    # Platinum condition
    cert = CertificationEngine.evaluate_certification(db, ds.id)
    assert cert.certification_level == "platinum"

    # Degrade report to trigger Bronze
    rep.health_score = 40.0
    db.commit()
    cert2 = CertificationEngine.evaluate_certification(db, ds.id)
    assert cert2.certification_level == "bronze"

def test_impact_analysis_risk_scoring(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    
    # 0 dependencies
    analysis1 = ImpactEngine.analyze_impact(db, ds.id, "schema_change")
    assert analysis1.risk_score == "LOW"

    # Setup parent-child lineage
    ds2 = Dataset(id=uuid.uuid4(), name="Ops Dataset Beta", owner_id=m4_setup_data["user"].id)
    db.add(ds2)
    db.commit()
    LineageEngine.add_dependency(db, ds.id, ds2.id, "derived_from")

    analysis2 = ImpactEngine.analyze_impact(db, ds.id, "schema_change")
    assert analysis2.risk_score == "HIGH" # 1 downstream with schema change

def test_monitoring_alerts_triggering_and_actions(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]

    # Ingest validation report
    rep = ValidationReport(
        dataset_version_id=ver.id, health_score=50.0, quality_score=50.0,
        drift_score=0.1, anomaly_score=0.0, report_json={}
    )
    db.add(rep)
    db.commit()

    # Rule: health_score < 70
    rule = MonitoringEngine.create_rule(db, ds.id, "health_score", 70.0, "<", "high")
    assert rule.metric == "health_score"

    alerts = MonitoringEngine.evaluate_rules(db, ver.id)
    assert len(alerts) == 1
    assert alerts[0].status == "OPEN"

    # Acknowledge
    ack = MonitoringEngine.acknowledge_alert(db, alerts[0].id, "auditor@domain.com")
    assert ack.status == "ACKNOWLEDGED"

    # Resolve
    res = MonitoringEngine.resolve_alert(db, alerts[0].id, "auditor@domain.com")
    assert res.status == "RESOLVED"

def test_automated_remediation_execution(db, m4_setup_data):
    ver = m4_setup_data["ver"]
    
    inc = DataIncident(
        dataset_version_id=ver.id, status="OPEN", severity="medium",
        title="Quality Breach", description="Violations count exceeds threshold"
    )
    db.add(inc)
    db.commit()

    action = RemediationEngine.trigger_remediation(db, inc.id, "reprofile_dataset")
    assert action.status == "SUCCESS"
    assert action.executed_at is not None

def test_governance_policy_evaluations(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    
    p1 = GovernanceEngine.create_policy(db, "PII Encryption Standard", "PII Compliance", "Require encryption", "high")
    p2 = GovernanceEngine.create_policy(db, "Data Freshness SLA Check", "Freshness Policy", "Delay limits", "medium")
    p3 = GovernanceEngine.create_policy(db, "Data Retention Limit", "Retention Policy", "Max versions", "low")
    p4 = GovernanceEngine.create_policy(db, "Data Schema Governance", "Schema Governance", "Data Contracts", "high")
    p5 = GovernanceEngine.create_policy(db, "Data Quality Standards", "Quality Standards", "Score standards", "medium")

    # Map them
    GovernanceEngine.map_policy(db, ds.id, p1.id)
    GovernanceEngine.map_policy(db, ds.id, p2.id)
    GovernanceEngine.map_policy(db, ds.id, p3.id)
    GovernanceEngine.map_policy(db, ds.id, p4.id)
    GovernanceEngine.map_policy(db, ds.id, p5.id)

    # 1. Evaluate default (no catalog or violations yet, so it should be compliant on retention/PII)
    snapshot = GovernanceEngine.evaluate_compliance(db, ds.id)
    assert snapshot.compliance_score == 100.0

    # 2. Trigger failures:
    # Retention Fail: Create 5 more dummy versions (total 6)
    for i in range(2, 7):
        v = DatasetVersion(
            dataset_id=ds.id, version_number=i, file_path="ops_data.csv",
            filename="ops_data.csv", mime_type="text/csv", file_size=10
        )
        db.add(v)
    db.commit()

    # Freshness Fail: Log critical delay record
    from src.models.freshness import DatasetFreshnessRecord
    rec = DatasetFreshnessRecord(
        dataset_id=ds.id, expected_refresh_time=datetime.utcnow(),
        delay_minutes=300, status="critical"
    )
    db.add(rec)

    # Schema Governance Fail: Add active contract violation
    from src.models.contract import ContractViolation
    cv = ContractViolation(
        contract_rule_id=uuid.uuid4(), dataset_version_id=v.id,
        severity="high", message="Mock contract rule violation"
    )
    db.add(cv)

    # Quality Standards Fail: Create validation report with health score < 80
    from src.models.reliability import ValidationReport
    rep = ValidationReport(
        dataset_version_id=v.id, health_score=50.0,
        quality_score=50.0, drift_score=0.1, anomaly_score=0.0, report_json={}
    )
    db.add(rep)
    db.commit()



    # PII Compliance Fail: Create sensitivity PUBLIC catalog with PII column
    from src.models.catalog import DatasetCatalog, ColumnCatalog
    catalog = DatasetCatalog(dataset_id=ds.id, data_owner="Admin", sensitivity_level="PUBLIC")
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    col = ColumnCatalog(dataset_catalog_id=catalog.id, column_name="email", semantic_type="PII")


    db.add(col)
    db.commit()

    snapshot2 = GovernanceEngine.evaluate_compliance(db, ds.id)
    assert snapshot2.compliance_score == 0.0


def test_dashboard_snapshots_and_scores(db, m4_setup_data):
    snapshot = CommandCenterEngine.generate_snapshot(db)
    assert snapshot.platform_health_score > 0.0

def test_api_endpoints_contracts(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    payload = {
        "dataset_id": str(ds.id),
        "name": "API Contract",
        "owner": "Developer",
        "description": "API defined contract specs",
        "contract_version": "1.0.0",
        "rules": [
            {"rule_type": "column_exists", "column_name": "id", "expected_value": "", "severity": "high"}
        ]
    }
    response = client.post("/api/v1/contracts", json=payload, headers=admin_headers)
    assert response.status_code == 201
    c_id = response.json()["id"]

    # List contracts
    res_list = client.get("/api/v1/contracts", headers=admin_headers)
    assert res_list.status_code == 200

    # Get contract
    res_get = client.get(f"/api/v1/contracts/{c_id}", headers=admin_headers)
    assert res_get.status_code == 200

    # Patch status
    res_patch = client.patch(f"/api/v1/contracts/{c_id}?status=active", headers=admin_headers)
    assert res_patch.status_code == 200

    # Get contract versions
    res_vers = client.get(f"/api/v1/contracts/{c_id}/versions", headers=admin_headers)
    assert res_vers.status_code == 200

    # Get contract violations
    res_viols = client.get(f"/api/v1/contracts/{c_id}/violations", headers=admin_headers)
    assert res_viols.status_code == 200

def test_api_endpoints_certifications(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    payload = {
        "dataset_id": str(ds.id),
        "approved_by": "Developer Auditor",
        "notes": "API Triggered"
    }
    response = client.post("/api/v1/certifications", json=payload, headers=admin_headers)
    assert response.status_code == 201

    # List
    res_list = client.get("/api/v1/certifications", headers=admin_headers)
    assert res_list.status_code == 200

    # Get
    res_get = client.get(f"/api/v1/certifications/{ds.id}", headers=admin_headers)
    assert res_get.status_code == 200

def test_api_endpoints_monitoring(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    payload = {
        "dataset_id": str(ds.id),
        "metric": "health_score",
        "threshold": 80.0,
        "comparison_operator": "<",
        "severity": "medium"
    }
    response = client.post("/api/v1/monitoring/rules", json=payload, headers=admin_headers)
    assert response.status_code == 201

    # Get rules
    res_rules = client.get("/api/v1/monitoring/rules", headers=admin_headers)
    assert res_rules.status_code == 200

    # Get alerts
    res_alerts = client.get("/api/v1/monitoring/alerts", headers=admin_headers)
    assert res_alerts.status_code == 200

def test_api_endpoints_alerts_actions(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    # Setup dummy alert
    rule = MonitoringEngine.create_rule(db, ds.id, "drift_score", 0.5, ">", "high")
    alert = MonitoringAlert(rule_id=rule.id, status="OPEN", message="Test alert message")
    db.add(alert)
    db.commit()

    # Acknowledge
    response = client.post(f"/api/v1/monitoring/alerts/{alert.id}/acknowledge", headers=admin_headers)
    assert response.status_code == 200

    # Resolve
    response = client.post(f"/api/v1/monitoring/alerts/{alert.id}/resolve", headers=admin_headers)
    assert response.status_code == 200

def test_api_endpoints_impact(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    response = client.post(f"/api/v1/impact/{ds.id}?change_type=schema_change", headers=admin_headers)
    assert response.status_code == 202

    # Get
    response_get = client.get(f"/api/v1/impact/{ds.id}", headers=admin_headers)
    assert response_get.status_code == 200

def test_api_endpoints_governance(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    payload = {
        "name": "API PII Encryption standard",
        "category": "PII Compliance",
        "description": "Standard",
        "severity": "high"
    }
    response = client.post("/api/v1/governance/policies", json=payload, headers=admin_headers)
    assert response.status_code == 201

    # List
    response_list = client.get("/api/v1/governance/policies", headers=admin_headers)
    assert response_list.status_code == 200

    # Get compliance history list
    response_compliance = client.get("/api/v1/governance/compliance", headers=admin_headers)
    assert response_compliance.status_code == 200

    # Get dataset specific
    response_ds = client.get(f"/api/v1/governance/compliance/{ds.id}", headers=admin_headers)
    assert response_ds.status_code == 200

def test_api_endpoints_dashboard(client, admin_headers, db, m4_setup_data):
    response = client.get("/api/v1/dashboard/reliability", headers=admin_headers)
    assert response.status_code == 200

    response = client.get("/api/v1/dashboard/incidents", headers=admin_headers)
    assert response.status_code == 200

    response = client.get("/api/v1/dashboard/compliance", headers=admin_headers)
    assert response.status_code == 200

    response = client.get("/api/v1/dashboard/history", headers=admin_headers)
    assert response.status_code == 200

def test_celery_tasks_milestone_4(db, m4_setup_data):
    ver = m4_setup_data["ver"]
    
    # Incident for remediation task
    inc = DataIncident(
        dataset_version_id=ver.id, status="OPEN", severity="medium",
        title="Quality Breach", description="Violations count exceeds threshold"
    )
    db.add(inc)
    db.commit()

    res1 = run_monitoring(str(ver.id))
    assert "Monitoring completed" in res1

    res2 = evaluate_contracts(str(ver.id))
    assert "Contract evaluation finished" in res2

    res3 = execute_remediation(str(inc.id), "reprofile_dataset")
    assert "executed" in res3

    res4 = calculate_platform_reliability()
    assert "Reliability score calculated" in res4

def test_extra_contract_validation_error_paths(db, m4_setup_data):
    # Test validation with non-existent version ID
    violations = ContractEngine.validate_version(db, uuid.uuid4())
    assert len(violations) == 0

def test_extra_contract_validation_nonexistent_contract(db, m4_setup_data):
    # Test validation when no contract is registered
    ver = m4_setup_data["ver"]
    violations = ContractEngine.validate_version(db, ver.id, uuid.uuid4())
    assert len(violations) == 0

def test_extra_compliance_empty_policies(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    snapshot = GovernanceEngine.evaluate_compliance(db, ds.id)
    assert snapshot.compliance_score == 100.0

def test_extra_remediation_nonexistent_incident(db):
    action = RemediationAction(incident_id=uuid.uuid4(), action_type="reprofile_dataset", status="PENDING")
    db.add(action)
    db.commit()
    res = RemediationEngine.trigger_remediation(db, uuid.uuid4(), "reprofile_dataset")
    assert res.status == "FAILED"

def test_extra_monitoring_rule_invalid_metric(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]
    MonitoringEngine.create_rule(db, ds.id, "invalid_metric_name", 90.0, "<")
    alerts = MonitoringEngine.evaluate_rules(db, ver.id)
    assert len(alerts) == 0

def test_extra_monitoring_rule_invalid_operator(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    ver = m4_setup_data["ver"]
    MonitoringEngine.create_rule(db, ds.id, "health_score", 90.0, "INVALID_OP")
    alerts = MonitoringEngine.evaluate_rules(db, ver.id)
    assert len(alerts) == 0

def test_extra_monitoring_nonexistent_version(db):
    alerts = MonitoringEngine.evaluate_rules(db, uuid.uuid4())
    assert len(alerts) == 0

def test_extra_dashboard_history_retrieval(db, m4_setup_data):
    CommandCenterEngine.generate_snapshot(db)
    snapshots = db.query(ReliabilityDashboardSnapshot).all()
    assert len(snapshots) >= 1

def test_extra_monitoring_alert_acknowledgement_nonexistent(db):
    alert = MonitoringEngine.acknowledge_alert(db, uuid.uuid4(), "user@test.com")
    assert alert is None

def test_extra_monitoring_alert_resolution_nonexistent(db):
    alert = MonitoringEngine.resolve_alert(db, uuid.uuid4(), "user@test.com")
    assert alert is None

def test_extra_certification_expiration_checks(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    cert = CertificationEngine.evaluate_certification(db, ds.id)
    assert cert.expires_at is not None

def test_extra_impact_analysis_cycle_checks(db, m4_setup_data):
    ds = m4_setup_data["ds"]
    # Setup dependency mapping from ds -> ds (cycle)
    LineageEngine.add_dependency(db, ds.id, ds.id, "derived_from")
    res = ImpactEngine.analyze_impact(db, ds.id, "schema_change")
    assert res.risk_score is not None

def test_extra_api_contract_not_found(client, admin_headers):
    response = client.get(f"/api/v1/contracts/{uuid.uuid4()}", headers=admin_headers)
    assert response.status_code == 404

def test_extra_api_contract_patch_invalid_status(client, admin_headers, db, m4_setup_data):
    ds = m4_setup_data["ds"]
    contract = ContractEngine.create_contract(db, ds.id, "Test", "Owner")
    response = client.patch(f"/api/v1/contracts/{contract.id}?status=invalid_status", headers=admin_headers)
    assert response.status_code == 400

def test_extra_api_contracts_patch_not_found(client, admin_headers):
    response = client.patch(f"/api/v1/contracts/{uuid.uuid4()}?status=active", headers=admin_headers)
    assert response.status_code == 404

