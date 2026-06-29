import uuid
import pytest
from datetime import datetime, timedelta
from src.models.tenant import Tenant, TenantMember, TenantSettings
from src.models.feature_flag import FeatureFlag, FeatureFlagAudit
from src.models.retention import RetentionPolicy, DataPurgeExecution
from src.models.cost import CloudCostSnapshot, ComputeUsageMetric, StorageUsageMetric
from src.models.security_audit import SecurityAuditEvent

from src.services.secret_provider import SecretManager, EnvSecretProvider, VaultSecretProvider
from src.services.retention_engine import RetentionEngine
from src.services.cost_engine import CostEngine
from src.services.intelligence_score_engine import IntelligenceScoreEngine

@pytest.fixture
def m7_setup_data(db):
    tenant = Tenant(name="Enterprise Tenant")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    yield {"tenant": tenant}

def test_tenant_creation_and_membership(db, m7_setup_data):
    t = m7_setup_data["tenant"]
    member = TenantMember(tenant_id=t.id, user_id=uuid.uuid4(), role="Admin")
    db.add(member)
    db.commit()

    assert len(t.members) == 1
    assert t.members[0].role == "Admin"

def test_feature_flag_rollout(db):
    flag = FeatureFlag(key="new_ai_copilot_beta", description="Beta AI chat model", rollout_percentage=25, enabled=True)
    db.add(flag)
    db.commit()

    audit = FeatureFlagAudit(feature_flag_id=flag.id, action="ENABLED", changed_by="admin@engine.com")
    db.add(audit)
    db.commit()

    assert flag.rollout_percentage == 25
    assert len(flag.audits) == 1

def test_cost_engine_tenant_summary(db):
    CostEngine.log_compute_cost(db, "exec_123", "workflow", 500.0) # $0.05
    summary = CostEngine.calculate_tenant_cost(db)
    assert summary["total_estimated_spend"] == 0.05

def test_security_audit_logging(db):
    log = SecurityAuditEvent(event_type="rate_limit_breach", user_email="attacker@domain.com", details="IP rate limit exceeded")
    db.add(log)
    db.commit()
    assert log.event_type == "rate_limit_breach"

# --- API endpoints verification tests ---
def test_api_tenants(client, admin_headers, db):
    payload = {"name": "SaaS Tenant"}
    response = client.post("/api/v1/tenants", json=payload, headers=admin_headers)
    assert response.status_code == 201
    tenant_id = response.json()["id"]

    response_list = client.get("/api/v1/tenants", headers=admin_headers)
    assert response_list.status_code == 200

    response_members = client.get(f"/api/v1/tenants/{tenant_id}/members", headers=admin_headers)
    assert response_members.status_code == 200

def test_api_feature_flags(client, admin_headers, db):
    payload = {"key": "dark_mode_v2", "description": "New UI theme test", "rollout_percentage": 50}
    response = client.post("/api/v1/feature-flags", json=payload, headers=admin_headers)
    assert response.status_code == 201

    response_list = client.get("/api/v1/feature-flags", headers=admin_headers)
    assert response_list.status_code == 200

def test_api_retention(client, admin_headers, db):
    from src.models.dataset import Dataset
    ds = Dataset(id=uuid.uuid4(), name="Retention Dataset", owner_id=uuid.uuid4())
    db.add(ds)
    db.commit()

    payload = {"dataset_id": str(ds.id), "retention_days": 15}
    response = client.post("/api/v1/retention", json=payload, headers=admin_headers)
    assert response.status_code == 201

    response_purge = client.post(f"/api/v1/retention/execute/{ds.id}", headers=admin_headers)
    assert response_purge.status_code == 200

    response_executions = client.get("/api/v1/retention/executions", headers=admin_headers)
    assert response_executions.status_code == 200
