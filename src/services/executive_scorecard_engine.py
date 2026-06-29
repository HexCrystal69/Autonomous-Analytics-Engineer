from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from src.models.scorecard import ExecutiveScorecard, ReliabilityScorecard
from src.models.dataset import Dataset, DatasetVersion
from src.models.observability import DataIncident
from src.models.sla import DatasetSLA

class ExecutiveScorecardEngine:
    @staticmethod
    def generate(db: Session) -> ExecutiveScorecard:
        """
        Gathers platform-wide statistics to compile the executive dashboard report.
        """
        # Count datasets
        total_datasets = db.query(Dataset).count()

        # Platform score: average of the latest reliability scorecard scores
        subq = db.query(
            ReliabilityScorecard.dataset_version_id,
            func.max(ReliabilityScorecard.created_at).label("max_date")
        ).group_by(ReliabilityScorecard.dataset_version_id).subquery()

        avg_reliability = db.query(func.avg(ReliabilityScorecard.reliability_score))\
            .join(subq, ReliabilityScorecard.dataset_version_id == subq.c.dataset_version_id)\
            .scalar()

        platform_score = round(float(avg_reliability), 2) if avg_reliability is not None else 100.0

        # Critical incidents
        critical_incidents = db.query(DataIncident).filter(
            DataIncident.status == "OPEN",
            DataIncident.severity.in_(["critical", "high"])
        ).count()

        # SLA compliance average
        avg_sla = db.query(func.avg(DatasetSLA.compliance_pct)).scalar()
        sla_compliance = round(float(avg_sla), 2) if avg_sla is not None else 100.0

        # Identify top risks: latest scorecards with the lowest scores
        low_scorecards = db.query(ReliabilityScorecard)\
            .order_by(ReliabilityScorecard.reliability_score.asc())\
            .limit(5)\
            .all()

        top_risks = []
        for sc in low_scorecards:
            ver = db.query(DatasetVersion).filter(DatasetVersion.id == sc.dataset_version_id).first()
            if ver:
                ds = db.query(Dataset).filter(Dataset.id == ver.dataset_id).first()
                if ds:
                    top_risks.append({
                        "dataset_name": ds.name,
                        "version": ver.version_number,
                        "reliability_score": sc.reliability_score,
                        "classification": sc.classification
                    })

        scorecard = ExecutiveScorecard(
            overall_platform_score=platform_score,
            datasets_monitored=total_datasets,
            critical_incidents=critical_incidents,
            sla_compliance=sla_compliance,
            top_risks=top_risks
        )
        db.add(scorecard)
        db.commit()
        db.refresh(scorecard)
        return scorecard
