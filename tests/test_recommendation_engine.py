import uuid
from src.services.recommendation_engine import RecommendationEngine

def test_recommendation_empty_outputs(db):
    res = RecommendationEngine.generate(db, uuid.uuid4())
    assert len(res) == 0
