import time
import pytest
from src.services.cost_engine import CostEngine

def test_performance_cost_logging_latency(db):
    start = time.time()

    # Log 10 costs in quick succession to benchmark compute latency
    for i in range(10):
        CostEngine.log_compute_cost(db, f"res_{i}", "workflow", 200.0)

    duration = time.time() - start
    # Ensure average write time is fast (less than 5s overall)
    assert duration < 5.0

