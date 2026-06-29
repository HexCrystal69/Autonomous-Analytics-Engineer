import uuid
from src.services.root_cause_engine import RootCauseEngine
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion

def test_root_cause_nonexistent_version(db):
    res = RootCauseEngine.analyze(db, uuid.uuid4())
    assert len(res) == 0

def test_root_cause_empty_results(db):
    # Create user first
    user = User(
        id=uuid.uuid4(),
        email="rca_owner@test.com",
        hashed_password="dummy",
        role="Admin"
    )
    db.add(user)
    db.commit()

    ds = Dataset(id=uuid.uuid4(), name="Root Cause Dataset", owner_id=user.id)
    db.add(ds)
    db.commit()

    version = DatasetVersion(
        id=uuid.uuid4(),
        dataset_id=ds.id,
        version_number=1,
        file_path="dummy.csv",
        filename="dummy.csv",
        mime_type="text/csv",
        row_count=100,
        column_count=5,
        file_size=1000
    )
    db.add(version)
    db.commit()

    res = RootCauseEngine.analyze(db, version.id)
    assert len(res) == 0
