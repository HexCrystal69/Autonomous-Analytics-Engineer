from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.leaderboard import Leaderboard, LeaderboardHistory
from src.routes.auth import get_current_user

router = APIRouter(prefix="/api/v1/leaderboards", tags=["leaderboards"])

@router.get("")
def get_all_leaderboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lbs = db.query(Leaderboard).order_by(Leaderboard.category, Leaderboard.rank.asc()).all()
    return lbs

@router.get("/history")
def get_leaderboard_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = db.query(LeaderboardHistory).order_by(LeaderboardHistory.created_at.desc()).all()
    return history

@router.get("/{category}")
def get_leaderboard_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lbs = db.query(Leaderboard).filter(
        Leaderboard.category == category
    ).order_by(Leaderboard.rank.asc()).all()
    return lbs
