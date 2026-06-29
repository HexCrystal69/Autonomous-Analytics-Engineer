import io
import uuid
from src.models.dataset import Dataset, DatasetVersion
from src.models.quality import DataQualityRule
from src.models.profile import DatasetProfile
from src.models.user import User
from src.services.profiling import ProfilingEngine


def test_create_rule_success(client, admin_headers, db):
    csv_data = "col1,col2\n1,foo\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Rule Creation Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    dataset_id = up_res.json()["dataset_id"]

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={
            "rule_name": "Null Check Limit",
            "rule_type": "NULL_PERCENT",
            "threshold": 10.0,
            "enabled": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_name"] == "Null Check Limit"
    assert data["rule_type"] == "NULL_PERCENT"
    assert data["threshold"] == 10.0
    assert data["dataset_id"] == dataset_id

def test_list_rules(client, admin_headers, db):
    csv_data = "col1,col2\n1,foo\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Rule List Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    dataset_id = up_res.json()["dataset_id"]

    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Rule 1", "rule_type": "NULL_PERCENT", "threshold": 5.0}
    )

    response = client.get(f"/api/v1/datasets/{dataset_id}/rules", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_validate_version_rules(client, admin_headers, db):
    # Upload and profile dataset
    csv_data = "col1,col2\n1,foo\n2,bar\n,baz\n" # 1 null out of 6 cells = 16.67% null cells. col1 has 33% nulls
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Validation Dataset"},
        files={"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]
    dataset_id = up_res.json()["dataset_id"]

    # 1. Create rule: Overall nulls < 10% (Should FAIL)
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Null Limit Fail", "rule_type": "NULL_PERCENT", "threshold": 10.0}
    )

    # 2. Create rule: Duplicate rows < 5% (Should PASS)
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Dup Limit Pass", "rule_type": "DUPLICATE_PERCENT", "threshold": 5.0}
    )

    # 3. Create rule: Column col1 min >= 0 (Should PASS)
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Col Min Pass", "rule_type": "COLUMN_MIN:col1", "threshold": 0.0}
    )

    # 4. Create rule: Column col1 max <= 1 (Should FAIL, since max is 2)
    client.post(
        f"/api/v1/datasets/{dataset_id}/rules",
        headers=admin_headers,
        json={"rule_name": "Col Max Fail", "rule_type": "COLUMN_MAX:col1", "threshold": 1.0}
    )

    response = client.post(
        f"/api/v1/datasets/versions/{version_id}/validate",
        headers=admin_headers
    )
    assert response.status_code == 200
    report = response.json()
    assert report["all_passed"] is False
    validations = report["validations"]
    assert len(validations) == 4

    # Check passes and fails
    for v in validations:
        if v["rule_name"] == "Null Limit Fail":
            assert v["passed"] is False
        elif v["rule_name"] == "Dup Limit Pass":
            assert v["passed"] is True
        elif v["rule_name"] == "Col Min Pass":
            assert v["passed"] is True
        elif v["rule_name"] == "Col Max Fail":
            assert v["passed"] is False

def test_validate_version_not_profiled(client, admin_headers, db, test_user):
    # Create dataset manually without profile
    dataset = Dataset(name="Manual Dataset", owner_id=test_user.id)
    db.add(dataset)
    db.commit()

    
    version = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        file_path="mock_path.csv",
        filename="mock.csv",
        mime_type="text/csv",
        file_size=10
    )
    db.add(version)
    db.commit()

    response = client.post(
        f"/api/v1/datasets/versions/{version.id}/validate",
        headers=admin_headers
    )
    # Profile does not exist yet
    assert response.status_code == 400
    assert "must be profiled" in response.json()["detail"]

def test_validate_rules_missing_column(db):
    from src.models.quality import DataQualityRule
    profile_result = {
        "summary_metrics": {"missing_cells_percent": 0.0, "duplicate_rows_percent": 0.0},
        "columns_metadata": {}
    }
    rule = DataQualityRule(id=uuid.uuid4(), rule_name="Missing Col", rule_type="COLUMN_MIN:nonexistent", threshold=10.0, enabled=True)
    report = ProfilingEngine.validate_rules(profile_result, [rule])
    assert report["all_passed"] is False
    assert "not found in dataset" in report["validations"][0]["error_message"]

def test_validate_rules_non_numeric_min_max(db):
    from src.models.quality import DataQualityRule
    profile_result = {
        "summary_metrics": {"missing_cells_percent": 0.0, "duplicate_rows_percent": 0.0},
        "columns_metadata": {
            "cat_col": {"is_numeric": False, "missing_percent": 0.0}
        }
    }
    rule = DataQualityRule(id=uuid.uuid4(), rule_name="Min on Cat", rule_type="COLUMN_MIN:cat_col", threshold=10.0, enabled=True)
    report = ProfilingEngine.validate_rules(profile_result, [rule])
    assert report["all_passed"] is False
    assert "is not numeric" in report["validations"][0]["error_message"]

def test_validate_rules_unsupported_type(db):
    from src.models.quality import DataQualityRule
    profile_result = {
        "summary_metrics": {"missing_cells_percent": 0.0, "duplicate_rows_percent": 0.0},
        "columns_metadata": {}
    }
    rule = DataQualityRule(id=uuid.uuid4(), rule_name="Bad Type", rule_type="UNSUPPORTED_TYPE", threshold=10.0, enabled=True)
    report = ProfilingEngine.validate_rules(profile_result, [rule])
    assert report["all_passed"] is False
    assert "Unsupported rule type" in report["validations"][0]["error_message"]

def test_rbac_quality_rules_viewer_forbidden(client, viewer_headers, db):
    # Viewer should not be allowed to create rules
    response = client.post(
        f"/api/v1/datasets/{uuid.uuid4()}/rules",
        headers=viewer_headers,
        json={"rule_name": "Viewer Rule", "rule_type": "NULL_PERCENT", "threshold": 5.0}
    )
    assert response.status_code == 403

def test_rbac_quality_rules_editor_allowed(client, editor_headers, db, test_editor):
    # Setup dataset owner using user id of editor
    dataset = Dataset(name="Editor Rules Dataset", owner_id=test_editor.id)
    db.add(dataset)
    db.commit()

    response = client.post(
        f"/api/v1/datasets/{dataset.id}/rules",
        headers=editor_headers,
        json={"rule_name": "Editor Rule", "rule_type": "NULL_PERCENT", "threshold": 5.0}
    )
    assert response.status_code == 201



