import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.scorecard import ExecutiveScorecard, ReliabilityScorecard
from src.models.leaderboard import Leaderboard
from src.models.catalog import DatasetCatalog, ColumnCatalog
from src.routes.auth import get_current_user
from src.services.trend_engine import TrendEngine

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics-dashboard"])

@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sc = db.query(ExecutiveScorecard).order_by(ExecutiveScorecard.created_at.desc()).first()
    if not sc:
        # Default empty scorecard structure
        return {
            "overall_platform_score": 100.0,
            "datasets_monitored": 0,
            "critical_incidents": 0,
            "sla_compliance": 100.0,
            "top_risks": []
        }
    return sc

@router.get("/trends")
def get_platform_reliability_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Returns last 30 scorecard entries
    scs = db.query(ReliabilityScorecard).order_by(ReliabilityScorecard.created_at.asc()).limit(30).all()
    return scs

@router.get("/trends/forecast")
def get_trend_forecast(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    forecasts = TrendEngine.get_forecasts(db, dataset_id)
    return forecasts

@router.get("/top-issues")
def get_top_platform_risks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sc = db.query(ExecutiveScorecard).order_by(ExecutiveScorecard.created_at.desc()).first()
    if sc:
        return sc.top_risks
    return []

@router.get("/improvements")
def get_most_improved_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get standings for most_improved leaderboard
    lbs = db.query(Leaderboard).filter(
        Leaderboard.category == "most_improved"
    ).order_by(Leaderboard.rank.asc()).all()
    return lbs

@router.get("/catalog/{dataset_id}")
def get_semantic_catalog(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    catalog = db.query(DatasetCatalog).filter(DatasetCatalog.dataset_id == dataset_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Semantic catalog not found for dataset")
    
    cols = db.query(ColumnCatalog).filter(ColumnCatalog.dataset_catalog_id == catalog.id).all()
    return {
        "catalog_id": catalog.id,
        "dataset_id": catalog.dataset_id,
        "owner": catalog.data_owner,
        "sensitivity": catalog.sensitivity_level,
        "columns": cols
    }
