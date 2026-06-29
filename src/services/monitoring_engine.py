import uuid
import operator
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.monitoring import MonitoringRule, MonitoringAlert
from src.models.dataset import DatasetVersion
from src.models.reliability import ValidationReport
from src.models.freshness import DatasetFreshnessRecord

class MonitoringEngine:
    @staticmethod
    def create_rule(
        db: Session,
        dataset_id: uuid.UUID,
        metric: str,
        threshold: float,
        comparison_operator: str,
        severity: str = "medium"
    ) -> MonitoringRule:
        rule = MonitoringRule(
            dataset_id=dataset_id,
            metric=metric,
            threshold=threshold,
            comparison_operator=comparison_operator,
            severity=severity
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def evaluate_rules(
        db: Session,
        dataset_version_id: uuid.UUID,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> List[MonitoringAlert]:
        version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not version:
            return []

        rules = db.query(MonitoringRule).filter(MonitoringRule.dataset_id == version.dataset_id).all()
        if not rules:
            return []

        # Load metrics data
        report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == dataset_version_id).first()
        freshness = db.query(DatasetFreshnessRecord).filter(
            DatasetFreshnessRecord.dataset_id == version.dataset_id
        ).order_by(DatasetFreshnessRecord.recorded_at.desc()).first()


        triggered_alerts = []
        operators = {
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
            "==": operator.eq
        }

        for rule in rules:
            op_func = operators.get(rule.comparison_operator)
            if not op_func:
                continue

            actual_val = None
            if rule.metric == "health_score" and report:
                actual_val = report.health_score
            elif rule.metric == "quality_score" and report:
                actual_val = report.quality_score
            elif rule.metric == "drift_score" and report:
                actual_val = report.drift_score
            elif rule.metric == "freshness_delay" and freshness:
                actual_val = float(freshness.delay_minutes)
            elif rule.metric == "anomaly_count" and report:
                actual_val = float(report.anomaly_score) # uses anomaly score metric limit

            if actual_val is not None and op_func(actual_val, rule.threshold):
                # Trigger Alert
                msg = f"Metric '{rule.metric}' breached threshold {rule.comparison_operator} {rule.threshold}. Actual value: {actual_val}."
                alert = MonitoringAlert(
                    rule_id=rule.id,
                    status="OPEN",
                    message=msg,
                    trace_id=trace_id,
                    span_id=span_id
                )
                db.add(alert)
                triggered_alerts.append(alert)

        if triggered_alerts:
            db.commit()

        return triggered_alerts

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: uuid.UUID, user_email: str) -> Optional[MonitoringAlert]:
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
        if alert:
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by = user_email
            alert.acknowledged_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: uuid.UUID, user_email: str) -> Optional[MonitoringAlert]:
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
        if alert:
            alert.status = "RESOLVED"
            alert.resolved_by = user_email
            alert.resolved_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
        return alert
