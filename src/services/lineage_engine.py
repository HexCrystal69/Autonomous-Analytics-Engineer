import uuid
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from src.models.lineage_dependency import DatasetDependency
from src.models.dataset import Dataset

class LineageEngine:
    @staticmethod
    def get_upstream(db: Session, dataset_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Recursively traverses upstream dependencies."""
        visited: Set[uuid.UUID] = set()
        dependencies = []

        def traverse(curr_id: uuid.UUID):
            if curr_id in visited:
                return
            visited.add(curr_id)
            
            deps = db.query(DatasetDependency).filter(DatasetDependency.target_dataset_id == curr_id).all()
            for d in deps:
                ds = db.query(Dataset).filter(Dataset.id == d.source_dataset_id).first()
                dependencies.append({
                    "id": d.id,
                    "source_dataset_id": d.source_dataset_id,
                    "dataset_name": ds.name if ds else "Unknown",
                    "relationship_type": d.relationship_type
                })
                traverse(d.source_dataset_id)

        traverse(dataset_id)
        return dependencies

    @staticmethod
    def get_downstream(db: Session, dataset_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Recursively traverses downstream dependencies."""
        visited: Set[uuid.UUID] = set()
        dependencies = []

        def traverse(curr_id: uuid.UUID):
            if curr_id in visited:
                return
            visited.add(curr_id)
            
            deps = db.query(DatasetDependency).filter(DatasetDependency.source_dataset_id == curr_id).all()
            for d in deps:
                ds = db.query(Dataset).filter(Dataset.id == d.target_dataset_id).first()
                dependencies.append({
                    "id": d.id,
                    "target_dataset_id": d.target_dataset_id,
                    "dataset_name": ds.name if ds else "Unknown",
                    "relationship_type": d.relationship_type
                })
                traverse(d.target_dataset_id)

        traverse(dataset_id)
        return dependencies

    @classmethod
    def calculate_blast_radius(cls, db: Session, dataset_id: uuid.UUID) -> int:
        """Calculates the count of unique downstream datasets affected if the dataset fails."""
        downstream = cls.get_downstream(db, dataset_id)
        unique_targets = set(d["target_dataset_id"] for d in downstream)
        return len(unique_targets)

    @staticmethod
    def add_dependency(
        db: Session,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relationship: str = "derived_from"
    ) -> DatasetDependency:
        """Saves a relationship dependency link between source and target datasets."""
        dep = DatasetDependency(
            source_dataset_id=source_id,
            target_dataset_id=target_id,
            relationship_type=relationship
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep
