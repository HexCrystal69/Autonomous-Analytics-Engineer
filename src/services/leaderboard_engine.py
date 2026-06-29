import uuid
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.dataset import Dataset, DatasetVersion
from src.models.reliability import ValidationReport
from src.models.scorecard import ReliabilityScorecard
from src.models.leaderboard import Leaderboard, LeaderboardHistory

class LeaderboardEngine:
    @staticmethod
    def refresh(db: Session) -> List[Leaderboard]:
        """
        Recalculates leaderboards for all active datasets.
        Creates leaderboard histories to log rank movement.
        """
        datasets = db.query(Dataset).all()
        if not datasets:
            return []

        # Categories mapping
        categories = ["best_quality", "best_health", "lowest_drift", "lowest_anomalies", "most_improved", "best_overall"]
        refreshed_records = []

        # Find latest validation report & scorecard for each dataset
        latest_reports = {}
        dataset_improvements = {}
        
        for ds in datasets:
            versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == ds.id).order_by(DatasetVersion.version_number.desc()).all()
            if not versions:
                continue
            
            latest_ver = versions[0]
            report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == latest_ver.id).first()
            scorecard = db.query(ReliabilityScorecard).filter(ReliabilityScorecard.dataset_version_id == latest_ver.id).first()
            
            if report:
                latest_reports[ds.id] = {
                    "report": report,
                    "scorecard": scorecard
                }

                # Calculate improvement: latest health score - earliest health score
                earliest_ver = versions[-1]
                earliest_report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == earliest_ver.id).first()
                if earliest_report:
                    dataset_improvements[ds.id] = report.health_score - earliest_report.health_score
                else:
                    dataset_improvements[ds.id] = 0.0

        for cat in categories:
            # Sort dataset list based on category
            sorted_datasets = []
            for ds_id, data in latest_reports.items():
                score = 100.0
                if cat == "best_quality":
                    score = data["report"].quality_score
                elif cat == "best_health":
                    score = data["report"].health_score
                elif cat == "lowest_drift":
                    score = data["report"].drift_score
                elif cat == "lowest_anomalies":
                    score = data["report"].anomaly_score
                elif cat == "most_improved":
                    score = dataset_improvements.get(ds_id, 0.0)
                elif cat == "best_overall":
                    score = data["scorecard"].reliability_score if data["scorecard"] else 0.0
                
                sorted_datasets.append((ds_id, score))

            # Sort descending
            sorted_datasets.sort(key=lambda x: x[1], reverse=True)

            # Assign ranks and save
            for index, (ds_id, score) in enumerate(sorted_datasets):
                rank = index + 1
                
                # Fetch existing leaderboard record
                existing = db.query(Leaderboard).filter(
                    Leaderboard.dataset_id == ds_id,
                    Leaderboard.category == cat
                ).first()

                prev_rank = existing.rank if existing else None

                if existing:
                    # Update score and rank
                    existing.score = float(score)
                    existing.rank = rank
                    refreshed_records.append(existing)
                else:
                    existing = Leaderboard(
                        dataset_id=ds_id,
                        category=cat,
                        score=float(score),
                        rank=rank
                    )
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)
                    refreshed_records.append(existing)

                # Determine movement
                movement = "flat"
                if prev_rank is not None:
                    if rank < prev_rank: # Numerically lower rank means rank improvement (e.g. 3rd -> 1st)
                        movement = "up"
                    elif rank > prev_rank:
                        movement = "down"

                # Log history
                history = LeaderboardHistory(
                    leaderboard_id=existing.id,
                    previous_rank=prev_rank or rank,
                    current_rank=rank,
                    movement=movement
                )
                db.add(history)

        db.commit()
        return refreshed_records
