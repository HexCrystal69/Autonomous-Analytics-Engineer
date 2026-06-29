import io
import uuid
import pytest
from src.models.dataset import Dataset, DatasetVersion
from src.models.job import ProfilingJob
from src.models.lineage import DatasetLineage

def test_upload_csv_success(client, admin_headers):
    csv_data = "col1,col2\n1,foo\n2,bar\n"
    file = io.BytesIO(csv_data.encode("utf-8"))
    
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Test CSV Dataset"},
        files={"file": ("test.csv", file, "text/csv")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.csv"
    assert data["version_number"] == 1
    assert "id" in data

def test_upload_excel_success(client, admin_headers):
    # Setup mock excel bytes
    import pandas as pd
    df = pd.DataFrame({"col1": [1, 2], "col2": ["foo", "bar"]})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    out.seek(0)

    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Test Excel Dataset"},
        files={"file": ("test.xlsx", out, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.xlsx"
    assert data["version_number"] == 1

def test_upload_file_size_exceeded(client, admin_headers):
    large_data = "a" * (51 * 1024 * 1024) # 51MB
    file = io.BytesIO(large_data.encode("utf-8"))
    
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Large Dataset"},
        files={"file": ("large.csv", file, "text/csv")}
    )
    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]

def test_list_datasets(client, admin_headers, db):
    # Upload one dataset first
    csv_data = "id,value\n1,100\n"
    client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Dataset 1"},
        files={"file": ("d1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )

    response = client.get("/api/v1/datasets", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Dataset 1"
    assert "latest_version" in data[0]

def test_get_dataset_detail(client, admin_headers, db):
    csv_data = "id,value\n1,100\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Dataset Detail"},
        files={"file": ("d1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]
    dataset_id = up_res.json()["dataset_id"]

    response = client.get(f"/api/v1/datasets/{dataset_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dataset Detail"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["id"] == version_id

def test_get_dataset_not_found(client, admin_headers):
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/datasets/{random_uuid}", headers=admin_headers)
    assert response.status_code == 404

def test_create_new_version(client, admin_headers, db):
    csv_data = "id,value\n1,100\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Version Test"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    dataset_id = up_res.json()["dataset_id"]
    parent_version_id = up_res.json()["id"]

    csv_data_v2 = "id,value\n1,100\n2,200\n"
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/version",
        headers=admin_headers,
        data={"parent_version_id": parent_version_id, "transformation_type": "FILTER"},
        files={"file": ("v2.csv", io.BytesIO(csv_data_v2.encode("utf-8")), "text/csv")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == 2
    assert data["filename"] == "v2.csv"

    # Verify lineage created
    lineage = db.query(DatasetLineage).filter(DatasetLineage.child_dataset_version_id == uuid.UUID(data["id"])).first()
    assert lineage is not None
    assert lineage.parent_dataset_version_id == uuid.UUID(parent_version_id)
    assert lineage.transformation_type == "FILTER"

def test_create_version_dataset_not_found(client, admin_headers):
    random_uuid = str(uuid.uuid4())
    response = client.post(
        f"/api/v1/datasets/{random_uuid}/version",
        headers=admin_headers,
        files={"file": ("v2.csv", io.BytesIO(b"data"), "text/csv")}
    )
    assert response.status_code == 404

def test_trigger_profiling_manually(client, admin_headers, db):
    csv_data = "id,value\n1,100\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Manual Profile Test"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]

    response = client.post(
        f"/api/v1/datasets/versions/{version_id}/profile",
        headers=admin_headers
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] in ["PENDING", "PROCESSING", "SUCCESS"]
    assert data["dataset_version_id"] == version_id

def test_get_job_status(client, admin_headers, db):
    csv_data = "id,value\n1,100\n"
    up_res = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Job Status Test"},
        files={"file": ("v1.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    )
    version_id = up_res.json()["id"]

    # Check job status for the auto-triggered job
    job = db.query(ProfilingJob).filter(ProfilingJob.dataset_version_id == uuid.UUID(version_id)).first()
    assert job is not None

    response = client.get(f"/api/v1/datasets/jobs/{job.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)

def test_get_job_status_not_found(client, admin_headers):
    random_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/datasets/jobs/{random_uuid}", headers=admin_headers)
    assert response.status_code == 404
