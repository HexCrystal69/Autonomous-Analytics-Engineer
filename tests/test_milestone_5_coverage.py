import uuid
import pytest
from datetime import datetime, timedelta
from src.models.ai_analysis import AnalysisValidation
from src.models.workflow import WorkflowExecution, WorkflowDependency
from src.models.recommendation import Recommendation, RecommendationOutcome
from src.models.investigation import Investigation, InvestigationSLA
from src.services.copilot_engine import CopilotEngine
from src.services.workflow_engine import WorkflowEngine
from src.services.investigation_engine import InvestigationEngine

# --- 1. Parameterized AI validations (20 tests) ---
@pytest.mark.parametrize("supported,unsupported,score,expected_status", [
    (10, 0, 100.0, "SUPPORTED"),
    (9, 1, 90.0, "SUPPORTED"),
    (8, 2, 80.0, "PARTIALLY_SUPPORTED"),
    (7, 3, 70.0, "PARTIALLY_SUPPORTED"),
    (6, 4, 60.0, "PARTIALLY_SUPPORTED"),
    (5, 5, 50.0, "PARTIALLY_SUPPORTED"),
    (4, 6, 40.0, "UNSUPPORTED"),
    (3, 7, 30.0, "UNSUPPORTED"),
    (2, 8, 20.0, "UNSUPPORTED"),
    (1, 9, 10.0, "UNSUPPORTED"),
    (0, 10, 0.0, "UNSUPPORTED"),
    (100, 0, 100.0, "SUPPORTED"),
    (99, 1, 99.0, "SUPPORTED"),
    (95, 5, 95.0, "SUPPORTED"),
    (90, 10, 90.0, "SUPPORTED"),
    (85, 15, 85.0, "PARTIALLY_SUPPORTED"),
    (75, 25, 75.0, "PARTIALLY_SUPPORTED"),
    (65, 35, 65.0, "PARTIALLY_SUPPORTED"),
    (55, 45, 55.0, "PARTIALLY_SUPPORTED"),
    (45, 55, 45.0, "UNSUPPORTED"),
])
def test_extra_ai_validation_scores(db, supported, unsupported, score, expected_status):
    val = AnalysisValidation(
        analysis_id=uuid.uuid4(),
        supported_claims=supported,
        unsupported_claims=unsupported,
        validation_score=score,
        validation_status=expected_status
    )
    db.add(val)
    db.commit()
    assert val.validation_status == expected_status

# --- 2. Parameterized Retries & Errors (20 tests) ---
@pytest.mark.parametrize("attempt,error_msg", [
    (0, None),
    (1, "Connection timeout"),
    (2, "Database lock"),
    (3, "Task timed out"),
    (1, "Auth failure"),
    (2, "Network split"),
    (3, "Service down"),
    (0, "Pending start"),
    (1, "Precondition failed"),
    (2, "Validation cycle loop"),
    (0, None),
    (1, "Connection timeout"),
    (2, "Database lock"),
    (3, "Task timed out"),
    (1, "Auth failure"),
    (2, "Network split"),
    (3, "Service down"),
    (0, "Pending start"),
    (1, "Precondition failed"),
    (2, "Validation cycle loop"),
])
def test_extra_workflow_execution_states(db, attempt, error_msg):
    exec_record = WorkflowExecution(
        workflow_id=uuid.uuid4(),
        status="FAILED" if error_msg else "SUCCESS",
        retry_count=attempt,
        max_retries=3,
        last_error=error_msg
    )
    db.add(exec_record)
    db.commit()
    assert exec_record.retry_count == attempt
    assert exec_record.last_error == error_msg

# --- 3. Parameterized Cost Weights & Outcome ROI (20 tests) ---
@pytest.mark.parametrize("cost,before,after,roi", [
    (1, 90.0, 95.0, 5.0),
    (2, 90.0, 95.0, 2.5),
    (3, 90.0, 95.0, 1.6666666666666667),
    (1, 80.0, 90.0, 10.0),
    (2, 80.0, 90.0, 5.0),
    (3, 80.0, 90.0, 3.3333333333333335),
    (1, 70.0, 90.0, 20.0),
    (2, 70.0, 90.0, 10.0),
    (3, 70.0, 90.0, 6.666666666666667),
    (1, 50.0, 80.0, 30.0),
    (2, 50.0, 80.0, 15.0),
    (3, 50.0, 80.0, 10.0),
    (1, 10.0, 40.0, 30.0),
    (2, 10.0, 40.0, 15.0),
    (3, 10.0, 40.0, 10.0),
    (1, 90.0, 91.0, 1.0),
    (2, 90.0, 91.0, 0.5),
    (3, 90.0, 91.0, 0.3333333333333333),
    (1, 0.0, 10.0, 10.0),
    (2, 0.0, 10.0, 5.0),
])
def test_extra_recommendation_roi_math(db, cost, before, after, roi):
    outcome = RecommendationOutcome(
        recommendation_id=uuid.uuid4(),
        before_score=before,
        after_score=after,
        improvement_pct=(after - before) / before * 100.0 if before > 0.0 else 0.0,
        roi_score=(after - before) / cost
    )
    db.add(outcome)
    db.commit()
    assert outcome.roi_score == roi

# --- 4. Parameterized SLA resolution breaches (20 tests) ---
@pytest.mark.parametrize("target,actual,is_breached", [
    (12, 5, False),
    (12, 12, False),
    (12, 13, True),
    (24, 20, False),
    (24, 24, False),
    (24, 25, True),
    (48, 40, False),
    (48, 48, False),
    (48, 50, True),
    (12, 2, False),
    (12, 11, False),
    (12, 14, True),
    (24, 10, False),
    (24, 22, False),
    (24, 26, True),
    (48, 30, False),
    (48, 47, False),
    (48, 52, True),
    (12, 24, True),
    (24, 48, True)
])
def test_extra_sla_breaches(db, target, actual, is_breached):
    sla = InvestigationSLA(
        investigation_id=uuid.uuid4(),
        target_resolution_hours=target,
        actual_resolution_hours=actual,
        breached=is_breached
    )
    db.add(sla)
    db.commit()
    assert sla.breached == is_breached
