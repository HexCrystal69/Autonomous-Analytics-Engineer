from src.models.user import User

def test_register_user_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "password", "role": "Viewer"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "Viewer"
    assert "id" in data

def test_register_user_duplicate_email(client, test_user):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": test_user.email, "password": "password", "role": "Viewer"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(client, test_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client, test_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user.email, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "detail" in response.json()

def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "notfound@example.com", "password": "password"}
    )
    assert response.status_code == 401

def test_rbac_admin_allowed(client, admin_headers):
    # Try a resource that requires Admin/Editor role - e.g. upload file but send no file to trigger validation check
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers
    )
    # 422 Unprocessable Entity indicates the auth passed but the body validation failed
    assert response.status_code == 422

def test_rbac_viewer_forbidden(client, viewer_headers):
    response = client.post(
        "/api/v1/datasets/upload",
        headers=viewer_headers
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Operation not permitted for your role"

def test_decode_invalid_token(client):
    response = client.get(
        "/api/v1/datasets",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_missing_auth_header(client):
    response = client.get("/api/v1/datasets")
    assert response.status_code == 401

def test_register_admin_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "password", "role": "Admin"}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "Admin"
