import uuid
import json
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from src.models.impact import ImpactAnalysis
from src.services.lineage_engine import LineageEngine

class ImpactEngine:
    @staticmethod
    def analyze_impact(
        db: Session,
        dataset_id: uuid.UUID,
        change_type: str = "schema_change"
    ) -> ImpactAnalysis:
        visited: Set[uuid.UUID] = set()
        affected: List[str] = []

        # Traverse downstream nodes recursively with cycle detection
        def traverse(node_id: uuid.UUID):
            if node_id in visited:
                return # Avoid cycle loops
            visited.add(node_id)

            downstream = LineageEngine.get_downstream(db, node_id)
            for dep in downstream:
                child_id = dep["target_dataset_id"]
                if child_id not in visited:
                    affected.append(str(child_id))
                    traverse(child_id)

        traverse(dataset_id)

        blast_radius = len(affected)
        
        # Risk classification scoring rules
        if blast_radius > 3:
            risk = "CRITICAL"
        elif blast_radius > 1 or (change_type == "schema_change" and blast_radius > 0):
            risk = "HIGH"
        elif blast_radius == 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # Mock downstream report counts derived from blast radius count for simplicity
        reports_count = blast_radius * 2

        impact = ImpactAnalysis(
            dataset_id=dataset_id,
            change_type=change_type,
            affected_datasets=json.dumps(affected),
            affected_reports=reports_count,
            risk_score=risk
        )
        db.add(impact)
        db.commit()
        db.refresh(impact)
        return impact
