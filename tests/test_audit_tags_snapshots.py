import io
import uuid
import pytest
from src.models.dataset import DatasetTag, DatasetVersion
from src.models.audit import AuditLog
from src.models.snapshot import ProfileSnapshot

def test_dataset_upload_with_tags(client, admin_headers, db):
    csv_data = "col1,col2\n1,foo\n"
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Tagged Dataset", "tags": "finance, marketing, sales"},
        files={"file": ("tagged.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 201
    
    version_id = response.json()["id"]
    version = db.query(DatasetVersion).filter(DatasetVersion.id == uuid.UUID(version_id)).first()
    assert version is not None
    
    # Verify tags exist
    tags = db.query(DatasetTag).filter(DatasetTag.dataset_id == version.dataset_id).all()
    assert len(tags) == 3
    tag_names = [t.tag_name for t in tags]
    assert "finance" in tag_names
    assert "marketing" in tag_names
    assert "sales" in tag_names

def test_audit_log_generation(client, admin_headers, db):
    csv_data = "col1,col2\n1,foo\n"
    # 1. Upload dataset (generates dataset_uploaded and version_created)
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Audited Dataset"},
        files={"file": ("audit.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    dataset_id = response.json()["dataset_id"]
    version_id = response.json()["id"]

    # Verify audit logs in database
    logs = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    assert len(logs) >= 4 # profile_started, dataset_uploaded, version_created, profile_completed
    
    actions = [log.action for log in logs]
    assert "dataset_uploaded" in actions
    assert "version_created" in actions
    assert "profile_started" in actions
    assert "profile_completed" in actions

def test_profile_snapshot_generation(client, admin_headers, db):
    csv_data = "col1,col2\n1,foo\n2,bar\n"
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Snapshot Dataset"},
        files={"file": ("snapshot.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = response.json()["id"]

    # Verify snapshot history exists
    snapshots = db.query(ProfileSnapshot).filter(ProfileSnapshot.dataset_version_id == uuid.UUID(version_id)).all()
    assert len(snapshots) == 1
    assert "row_count" in snapshots[0].summary_metrics
    assert snapshots[0].summary_metrics["row_count"] == 2
