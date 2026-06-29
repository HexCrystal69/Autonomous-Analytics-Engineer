from src.services.leaderboard_engine import LeaderboardEngine

def test_leaderboard_refresh_empty(db):
    res = LeaderboardEngine.refresh(db)
    assert len(res) == 0
