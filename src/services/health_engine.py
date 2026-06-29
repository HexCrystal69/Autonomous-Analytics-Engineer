from typing import Dict, Any

class HealthEngine:
    @staticmethod
    def calculate_health_score(
        null_percent: float,
        duplicate_percent: float,
        num_violations: int,
        num_anomalies: int
    ) -> Dict[str, Any]:
        """
        Computes a deterministic health score from 0 to 100.
        Health Score = 100 - null_penalty - duplicate_penalty - violation_penalty - anomaly_penalty
        """
        # 1. Null Penalty (directly proportional to null percentage)
        null_penalty = min(null_percent, 25.0)

        # 2. Duplicate Penalty (directly proportional to duplicate row percentage)
        duplicate_penalty = min(duplicate_percent, 25.0)

        # 3. Violation Penalty (5.0 points per quality rule violation, capped at 30)
        violation_penalty = min(num_violations * 5.0, 30.0)

        # 4. Anomaly Penalty (2.0 points per anomaly point found, capped at 20)
        anomaly_penalty = min(num_anomalies * 2.0, 20.0)

        # Calculate score
        raw_score = 100.0 - (null_penalty + duplicate_penalty + violation_penalty + anomaly_penalty)
        health_score = float(max(0.0, min(raw_score, 100.0)))

        # Status Mapping
        if health_score >= 90.0:
            status = "Healthy"
        elif health_score >= 75.0:
            status = "Warning"
        elif health_score >= 50.0:
            status = "Degraded"
        else:
            status = "Critical"

        return {
            "health_score": health_score,
            "quality_score": float(max(0.0, 100.0 - (null_penalty + violation_penalty))),
            "anomaly_score": float(max(0.0, 100.0 - anomaly_penalty)),
            "status": status,
            "breakdown": {
                "null_penalty": null_penalty,
                "duplicate_penalty": duplicate_penalty,
                "violation_penalty": violation_penalty,
                "anomaly_penalty": anomaly_penalty
            }
        }
