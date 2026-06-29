from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.services.intelligence_score_engine import IntelligenceScoreEngine
from src.models.recommendation import Recommendation
from src.models.observability import DataIncident
from src.models.workflow import WorkflowExecution
from src.models.executive_report import ExecutiveReport
from src.models.investigation import Investigation

router = APIRouter(prefix="/api/v1/intelligence", tags=["Platform Intelligence Dashboard"])

@router.get("/overview")
def get_intelligence_overview(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return IntelligenceScoreEngine.calculate_intelligence_score(db)

@router.get("/recommendations")
def get_dashboard_recommendations(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    recs = db.query(Recommendation).all()
    return [{"id": r.id, "title": r.title, "priority": r.priority, "status": r.status} for r in recs]

@router.get("/incidents")
def get_dashboard_incidents(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    incidents = db.query(DataIncident).all()
    return [{"id": i.id, "title": i.title, "status": i.status, "severity": i.severity} for i in incidents]

@router.get("/workflows")
def get_dashboard_workflows(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    execs = db.query(WorkflowExecution).all()
    return [{"id": e.id, "status": e.status, "retry_count": e.retry_count} for e in execs]

@router.get("/reports")
def get_dashboard_reports(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    reports = db.query(ExecutiveReport).all()
    return [{"id": r.id, "report_name": r.report_name, "quality_score": r.report_quality_score} for r in reports]

@router.get("/investigations")
def get_dashboard_investigations(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    invs = db.query(Investigation).all()
    return [{"id": i.id, "title": i.title, "status": i.status, "priority": i.priority} for i in invs]

@router.get("/top-risks")
def get_top_risks(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Highest open incidents and failures
    open_incidents = db.query(DataIncident).filter(DataIncident.status == "OPEN").order_by(DataIncident.created_at.desc()).limit(5).all()
    return [{"id": i.id, "title": i.title, "severity": i.severity} for i in open_incidents]

@router.get("/top-datasets")
def get_top_datasets(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    from src.models.dataset import Dataset
    datasets = db.query(Dataset).limit(5).all()
    return [{"id": d.id, "name": d.name} for d in datasets]

@router.get("/executive-brief")
def get_executive_brief(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    scores = IntelligenceScoreEngine.calculate_intelligence_score(db)
    return {
        "summary": "Platform is overall stable with active AI validations.",
        "kpis": scores
    }
