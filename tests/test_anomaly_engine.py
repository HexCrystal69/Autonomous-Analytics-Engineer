import pandas as pd
import numpy as np
import pytest
from src.services.anomaly_engine import AnomalyEngine

def test_detect_zscore():
    data = {"col1": [10.0, 10.1, 10.2, 9.9, 9.8, 10.0, 10.1, 10.0, 9.9, 20.0]} # 20.0 is an outlier
    df = pd.DataFrame(data)
    anomalies = AnomalyEngine.detect_zscore(df, threshold=2.0)
    assert len(anomalies) == 1
    assert anomalies[0]["column_name"] == "col1"
    assert anomalies[0]["row_index"] == 9
    assert anomalies[0]["anomaly_type"] == "Z_SCORE"

def test_detect_zscore_no_numerical():
    df = pd.DataFrame({"col1": ["a", "b", "c"]})
    anomalies = AnomalyEngine.detect_zscore(df)
    assert len(anomalies) == 0

def test_detect_iqr():
    data = {"col1": [10.0, 10.1, 10.2, 9.9, 9.8, 10.0, 10.1, 10.0, 9.9, 20.0]} # 20.0 is an outlier
    df = pd.DataFrame(data)
    anomalies = AnomalyEngine.detect_iqr(df)
    assert len(anomalies) == 1
    assert anomalies[0]["row_index"] == 9
    assert anomalies[0]["anomaly_type"] == "IQR"

def test_detect_isolation_forest():
    # Make a larger dataset for Isolation Forest
    np.random.seed(42)
    normal = np.random.normal(loc=10.0, scale=1.0, size=(100, 2))
    outliers = np.array([[25.0, 25.0], [-10.0, -10.0]])
    data = np.vstack([normal, outliers])
    df = pd.DataFrame(data, columns=["col1", "col2"])

    anomalies = AnomalyEngine.detect_isolation_forest(df, contamination=0.03)
    assert len(anomalies) >= 1
    assert any(a["row_index"] in [100, 101] for a in anomalies)

def test_detect_local_outlier_factor():
    np.random.seed(42)
    normal = np.random.normal(loc=10.0, scale=1.0, size=(100, 2))
    outliers = np.array([[25.0, 25.0]])
    data = np.vstack([normal, outliers])
    df = pd.DataFrame(data, columns=["col1", "col2"])

    anomalies = AnomalyEngine.detect_local_outlier_factor(df, contamination=0.03)
    assert len(anomalies) >= 1
    assert any(a["row_index"] == 100 for a in anomalies)

def test_detect_zscore_zero_std():
    # Columns with identical values will have 0 std
    df = pd.DataFrame({"col1": [5.0, 5.0, 5.0, 5.0, 5.0]})
    anomalies = AnomalyEngine.detect_zscore(df)
    assert len(anomalies) == 0

def test_detect_iqr_zero_iqr():
    df = pd.DataFrame({"col1": [5.0, 5.0, 5.0, 5.0, 5.0]})
    anomalies = AnomalyEngine.detect_iqr(df)
    assert len(anomalies) == 0

def test_detect_ml_too_small():
    # Isolation forest requires enough elements (>= 5)
    df = pd.DataFrame({"col1": [1, 2]})
    anomalies_if = AnomalyEngine.detect_isolation_forest(df)
    anomalies_lof = AnomalyEngine.detect_local_outlier_factor(df)
    assert len(anomalies_if) == 0
    assert len(anomalies_lof) == 0

