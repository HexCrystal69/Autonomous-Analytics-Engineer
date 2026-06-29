import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import User
from src.routes.auth import get_current_user, require_role
from src.services.lineage_engine import LineageEngine

router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])

@router.post("/dependency", status_code=status.HTTP_201_CREATED)
def register_dependency(
    source_dataset_id: uuid.UUID,
    target_dataset_id: uuid.UUID,
    relationship_type: str = "derived_from",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Editor"]))
):
    dep = LineageEngine.add_dependency(db, source_dataset_id, target_dataset_id, relationship_type)
    return dep

@router.get("/{dataset_id}")
def get_lineage_graph(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    upstream = LineageEngine.get_upstream(db, dataset_id)
    downstream = LineageEngine.get_downstream(db, dataset_id)
    blast_radius = LineageEngine.calculate_blast_radius(db, dataset_id)

    return {
        "dataset_id": dataset_id,
        "blast_radius": blast_radius,
        "upstream_dependencies": upstream,
        "downstream_dependencies": downstream
    }

@router.get("/{dataset_id}/upstream")
def get_upstream_lineage(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return LineageEngine.get_upstream(db, dataset_id)

@router.get("/{dataset_id}/downstream")
def get_downstream_lineage(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return LineageEngine.get_downstream(db, dataset_id)
