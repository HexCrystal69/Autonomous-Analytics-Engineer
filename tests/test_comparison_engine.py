import io
import uuid
import pytest
from src.services.comparison_engine import ComparisonEngine
from src.models.comparison import DatasetComparison

def test_comparison_engine_missing_versions(db):
    with pytest.raises(ValueError):
        ComparisonEngine.compare_versions(db, uuid.uuid4(), uuid.uuid4())

def test_comparison_delta_calculations(client, admin_headers, db):
    # Register source version
    csv_src = "col1,col2\n1,foo\n2,bar\n"
    up_src = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Comparison Dataset"},
        files={"file": ("v1.csv", io.BytesIO(csv_src.encode("utf-8")), "text/csv")}
    )
    src_id = up_src.json()["id"]
    dataset_id = up_src.json()["dataset_id"]

    # Register target version (added rows, added cols)
    csv_targ = "col1,col2,col3\n1,foo,99\n2,bar,99\n3,baz,99\n"
    up_targ = client.post(
        f"/api/v1/datasets/{dataset_id}/version",
        headers=admin_headers,
        files={"file": ("v2.csv", io.BytesIO(csv_targ.encode("utf-8")), "text/csv")}
    )
    targ_id = up_targ.json()["id"]

    # Run comparison
    comparison = ComparisonEngine.compare_versions(db, uuid.UUID(src_id), uuid.UUID(targ_id))
    assert comparison.row_delta == 1
    assert comparison.column_delta == 1
    
    # Verify records persisted in DB
    db_record = db.query(DatasetComparison).filter(DatasetComparison.id == comparison.id).first()
    assert db_record is not None
    assert len(db_record.columns) == 2 # col1, col2 compared (col3 was not in source)
