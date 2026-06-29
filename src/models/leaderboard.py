import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False) # best_quality, best_health, lowest_drift, lowest_anomalies, most_improved, best_overall
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    history = relationship("LeaderboardHistory", back_populates="leaderboard", cascade="all, delete-orphan")

class LeaderboardHistory(Base):
    __tablename__ = "leaderboard_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    leaderboard_id = Column(Uuid, ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False)
    previous_rank = Column(Integer, nullable=False)
    current_rank = Column(Integer, nullable=False)
    movement = Column(String, nullable=False) # up, down, flat
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    leaderboard = relationship("Leaderboard", back_populates="history")
