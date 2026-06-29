import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.routes.auth import get_current_user
from src.models.ai_analysis import AIAnalysis
from src.services.copilot_engine import CopilotEngine

router = APIRouter(prefix="/api/v1/ai", tags=["AI Intelligence Copilot"])

@router.post("/explain/incident/{id}")
def explain_incident(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        analysis = CopilotEngine.explain_incident(db, id)
        return {"id": analysis.id, "prompt_used": analysis.prompt_used, "response_text": analysis.response_text, "confidence_score": analysis.confidence_score, "status": analysis.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/explain/dataset/{id}")
def explain_dataset(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        analysis = CopilotEngine.explain_dataset(db, id)
        return {"id": analysis.id, "prompt_used": analysis.prompt_used, "response_text": analysis.response_text, "confidence_score": analysis.confidence_score, "status": analysis.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analysis/{id}")
def get_analysis(id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    analysis = db.query(AIAnalysis).filter(AIAnalysis.id == id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"id": analysis.id, "response_text": analysis.response_text, "confidence_score": analysis.confidence_score, "status": analysis.status}

@router.get("/analyses")
def list_analyses(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    analyses = db.query(AIAnalysis).all()
    return [{"id": a.id, "analysis_type": a.analysis_type, "status": a.status, "confidence_score": a.confidence_score} for a in analyses]
