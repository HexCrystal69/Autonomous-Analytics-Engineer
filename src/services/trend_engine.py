import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from src.models.dataset import DatasetVersion
from src.models.reliability import ValidationReport

class TrendEngine:
    @staticmethod
    def calculate_linear_regression_forecast(y: List[float]) -> float:
        """
        Calculates the next value in the series using linear regression.
        y: list of historical scores.
        """
        n = len(y)
        if n == 0:
            return 100.0
        if n == 1:
            return y[0]

        X = list(range(n))
        x_bar = sum(X) / n
        y_bar = sum(y) / n

        num = sum((X[i] - x_bar) * (y[i] - y_bar) for i in range(n))
        den = sum((X[i] - x_bar) ** 2 for i in range(n))

        if den == 0:
            return y[-1]

        slope = num / den
        intercept = y_bar - slope * x_bar

        # Forecast next value (index = n)
        forecast = intercept + slope * n
        return float(max(0.0, min(forecast, 100.0)))

    @staticmethod
    def calculate_moving_average_forecast(y: List[float], window: int = 3) -> float:
        """Calculates moving average forecast of the last 'window' elements."""
        if not y:
            return 100.0
        sub = y[-window:]
        return float(sum(sub) / len(sub))

    @classmethod
    def get_forecasts(cls, db: Session, dataset_id: uuid.UUID) -> Dict[str, Any]:

        """Fetches historical validation report scores for a dataset and returns forecasts."""
        versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).all()
        version_ids = [v.id for v in versions]

        reports = db.query(ValidationReport).filter(
            ValidationReport.dataset_version_id.in_(version_ids)
        ).order_by(ValidationReport.created_at.asc()).all()

        health_scores = [r.health_score for r in reports]
        quality_scores = [r.quality_score for r in reports]
        anomaly_scores = [r.anomaly_score for r in reports]
        drift_scores = [r.drift_score for r in reports]

        return {
            "health": {
                "history": health_scores,
                "regression_forecast": cls.calculate_linear_regression_forecast(health_scores),
                "moving_average_forecast": cls.calculate_moving_average_forecast(health_scores)
            },
            "quality": {
                "history": quality_scores,
                "regression_forecast": cls.calculate_linear_regression_forecast(quality_scores),
                "moving_average_forecast": cls.calculate_moving_average_forecast(quality_scores)
            },
            "anomaly": {
                "history": anomaly_scores,
                "regression_forecast": cls.calculate_linear_regression_forecast(anomaly_scores),
                "moving_average_forecast": cls.calculate_moving_average_forecast(anomaly_scores)
            },
            "drift": {
                "history": drift_scores,
                "regression_forecast": cls.calculate_linear_regression_forecast(drift_scores),
                "moving_average_forecast": cls.calculate_moving_average_forecast(drift_scores)
            }
        }
