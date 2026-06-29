def test_health_check_success(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "redis" in data
    assert "celery" in data
    assert "storage" in data
    assert "disk_usage" in data
    assert "queue_depth" in data

def test_metrics_success(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "# HELP" in response.text

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "running"
