import uuid
from typing import Optional
from sqlalchemy.orm import Session
from src.models.scorecard import ReliabilityScorecard

class ReliabilityEngine:
    @staticmethod
    def generate_scorecard(
        db: Session,
        dataset_version_id: uuid.UUID,
        health_score: float,
        quality_score: float,
        drift_score: float,
        anomaly_score: float,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> ReliabilityScorecard:
        """
        Calculates the overall Reliability Score:
        Reliability = 40% Health + 30% Quality + 20% Drift + 10% Anomaly
        Classifies and persists the ReliabilityScorecard.
        """
        reliability_score = (
            0.40 * health_score +
            0.30 * quality_score +
            0.20 * drift_score +
            0.10 * anomaly_score
        )
        reliability_score = float(max(0.0, min(reliability_score, 100.0)))

        # Classification mapping
        if reliability_score >= 90.0:
            classification = "excellent"
        elif reliability_score >= 75.0:
            classification = "good"
        elif reliability_score >= 50.0:
            classification = "warning"
        else:
            classification = "critical"

        scorecard = ReliabilityScorecard(
            dataset_version_id=dataset_version_id,
            health_score=health_score,
            quality_score=quality_score,
            anomaly_score=anomaly_score,
            drift_score=drift_score,
            reliability_score=reliability_score,
            classification=classification,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(scorecard)
        db.commit()
        db.refresh(scorecard)
        return scorecard
