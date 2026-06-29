from src.services.health_engine import HealthEngine

def test_health_score_perfect():
    res = HealthEngine.calculate_health_score(
        null_percent=0.0,
        duplicate_percent=0.0,
        num_violations=0,
        num_anomalies=0
    )
    assert res["health_score"] == 100.0
    assert res["status"] == "Healthy"

def test_health_score_warning():
    res = HealthEngine.calculate_health_score(
        null_percent=5.0, # 5 penalty
        duplicate_percent=5.0, # 5 penalty
        num_violations=1, # 5 penalty
        num_anomalies=0
    )
    # Total penalty = 15. Score = 85.
    assert res["health_score"] == 85.0
    assert res["status"] == "Warning"

def test_health_score_degraded():
    res = HealthEngine.calculate_health_score(
        null_percent=10.0, # 10 penalty
        duplicate_percent=10.0, # 10 penalty
        num_violations=3, # 15 penalty
        num_anomalies=0
    )
    # Total penalty = 35. Score = 65.
    assert res["health_score"] == 65.0
    assert res["status"] == "Degraded"

def test_health_score_critical():
    res = HealthEngine.calculate_health_score(
        null_percent=30.0, # 25 max penalty
        duplicate_percent=30.0, # 25 max penalty
        num_violations=10, # 30 max penalty
        num_anomalies=20 # 20 max penalty
    )
    # Total penalty = 100. Score = 0.
    assert res["health_score"] == 0.0
    assert res["status"] == "Critical"

def test_health_score_clamping():
    res = HealthEngine.calculate_health_score(
        null_percent=100.0,
        duplicate_percent=100.0,
        num_violations=100,
        num_anomalies=100
    )
    assert res["health_score"] == 0.0
    assert res["status"] == "Critical"
