import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.models.observability import DataIncident, IncidentComment, IncidentAssignment
from src.routes.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

@router.get("")
def list_incidents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    incidents = db.query(DataIncident).order_by(DataIncident.created_at.desc()).all()
    return incidents

@router.get("/{id}")
def get_incident_details(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inc = db.query(DataIncident).filter(DataIncident.id == id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    comments = db.query(IncidentComment).filter(IncidentComment.incident_id == id).order_by(IncidentComment.created_at.asc()).all()
    assignments = db.query(IncidentAssignment).filter(IncidentAssignment.incident_id == id).all()

    return {
        "id": inc.id,
        "dataset_version_id": inc.dataset_version_id,
        "status": inc.status,
        "severity": inc.severity,
        "title": inc.title,
        "description": inc.description,
        "created_at": inc.created_at,
        "comments": comments,
        "assignments": assignments
    }

@router.post("/{id}/assign", status_code=status.HTTP_200_OK)
def assign_incident(
    id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    inc = db.query(DataIncident).filter(DataIncident.id == id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    user_exists = db.query(User).filter(User.id == user_id).first()
    if not user_exists:
        raise HTTPException(status_code=400, detail="Target user does not exist")

    # Add assignment
    assignment = IncidentAssignment(incident_id=id, user_id=user_id)
    db.add(assignment)

    # Change status to INVESTIGATING
    inc.status = "INVESTIGATING"

    db.add(IncidentComment(
        incident_id=id,
        comment=f"Incident assigned to user {user_id}."
    ))

    db.commit()
    return {"message": "Incident successfully assigned", "status": inc.status}

@router.post("/{id}/comments", status_code=status.HTTP_201_CREATED)
def add_incident_comment(
    id: uuid.UUID,
    comment: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inc = db.query(DataIncident).filter(DataIncident.id == id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    record = IncidentComment(incident_id=id, user_id=current_user.id, comment=comment)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
