import pandas as pd
import numpy as np
import pytest
from src.services.drift_engine import DriftEngine

def test_psi_calculation_no_drift():
    # Identical distributions
    baseline = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10)
    target = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10)
    psi = DriftEngine.calculate_psi(baseline, target)
    assert psi < 0.05

def test_psi_calculation_high_drift():
    # Distinct distributions
    baseline = np.random.normal(10, 1, 100)
    target = np.random.normal(15, 1, 100)
    psi = DriftEngine.calculate_psi(baseline, target)
    assert psi > 0.25

def test_calculate_drift_numerical_shifts():
    df_base = pd.DataFrame({"col1": [10, 10, 10, 10, 10]})
    df_targ = pd.DataFrame({"col1": [15, 15, 15, 15, 15]}) # 50% shift

    drift_report = DriftEngine.calculate_drift(df_base, df_targ)
    results = drift_report["results"]
    
    # We should have MEAN_SHIFT metric
    mean_shift = [r for r in results if r["drift_metric"] == "MEAN_SHIFT"][0]
    assert mean_shift["drift_score"] == 0.50
    assert mean_shift["severity"] == "HIGH"

def test_calculate_drift_categorical_drift():
    df_base = pd.DataFrame({"col1": ["A", "A", "A", "A", "B", "B", "B", "B"]}) # 50% A, 50% B
    df_targ = pd.DataFrame({"col1": ["A", "A", "A", "A", "A", "A", "A", "B"]}) # 87.5% A, 12.5% B
    
    drift_report = DriftEngine.calculate_drift(df_base, df_targ)
    results = drift_report["results"]
    
    dist_drift = [r for r in results if r["drift_metric"] == "DIST_DRIFT"][0]
    # prop diff is 0.375. Overall sum of absolute diff is abs(0.5-0.875) + abs(0.5-0.125) = 0.375 + 0.375 = 0.75. Cap normalized is 0.75 / 2.0 = 0.375
    assert dist_drift["drift_score"] == 0.375
    assert dist_drift["severity"] == "HIGH"

def test_calculate_drift_cardinality():
    df_base = pd.DataFrame({"col1": ["A", "B", "C"]})
    df_targ = pd.DataFrame({"col1": ["A", "B", "C", "D", "E", "F"]}) # Cardinality doubled (100% drift)
    
    drift_report = DriftEngine.calculate_drift(df_base, df_targ)
    results = drift_report["results"]
    
    card_drift = [r for r in results if r["drift_metric"] == "CARD_DRIFT"][0]
    assert card_drift["drift_score"] == 1.0
    assert card_drift["severity"] == "HIGH"

def test_psi_calculation_empty_arrays():
    psi = DriftEngine.calculate_psi(np.array([]), np.array([]))
    assert psi == 0.0

def test_calculate_drift_zero_baseline_mean():
    df_base = pd.DataFrame({"col1": [0, 0, 0]})
    df_targ = pd.DataFrame({"col1": [5, 5, 5]}) # shift from 0 mean
    drift_report = DriftEngine.calculate_drift(df_base, df_targ)
    results = drift_report["results"]
    mean_shift = [r for r in results if r["drift_metric"] == "MEAN_SHIFT"][0]
    assert mean_shift["drift_score"] == 5.0

def test_calculate_drift_distribution_no_common_keys():
    df_base = pd.DataFrame({"col1": ["A", "B"]})
    df_targ = pd.DataFrame({"col1": ["C", "D"]})
    drift_report = DriftEngine.calculate_drift(df_base, df_targ)
    results = drift_report["results"]
    dist_drift = [r for r in results if r["drift_metric"] == "DIST_DRIFT"][0]
    assert dist_drift["drift_score"] == 1.0

