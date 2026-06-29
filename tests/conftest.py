import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

# Override database URL for tests to use an in-memory SQLite
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["STORAGE_DIR"] = "test_storage_data"

from src.database import Base, get_db
from src.main import app
from src.celery_app import celery_app
from src.utils.auth import hash_password

# Use SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


# Make celery tasks run synchronously during tests
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except Exception:
            pass

    import shutil
    if os.path.exists("test_storage_data"):
        shutil.rmtree("test_storage_data", ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_db():
    # Clean tables before each test
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()

@pytest.fixture
def db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    from src.models.user import User
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role="Admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_editor(db):
    from src.models.user import User
    user = User(
        email="editor@example.com",
        hashed_password=hash_password("password123"),
        role="Editor"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_viewer(db):
    from src.models.user import User
    user = User(
        email="viewer@example.com",
        hashed_password=hash_password("password123"),
        role="Viewer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_headers(client, test_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def editor_headers(client, test_editor):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_editor.email, "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def viewer_headers(client, test_viewer):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_viewer.email, "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
