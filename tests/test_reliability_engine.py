import uuid
from src.services.reliability_engine import ReliabilityEngine

def test_reliability_scorecard_excellent(db):
    sc = ReliabilityEngine.generate_scorecard(
        db=db,
        dataset_version_id=uuid.uuid4(),
        health_score=100.0,
        quality_score=100.0,
        drift_score=100.0,
        anomaly_score=100.0
    )
    assert sc.reliability_score == 100.0
    assert sc.classification == "excellent"

def test_reliability_scorecard_critical(db):
    sc = ReliabilityEngine.generate_scorecard(
        db=db,
        dataset_version_id=uuid.uuid4(),
        health_score=10.0,
        quality_score=10.0,
        drift_score=10.0,
        anomaly_score=10.0
    )
    assert sc.reliability_score == 10.0
    assert sc.classification == "critical"
