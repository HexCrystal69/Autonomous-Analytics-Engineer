import pandas as pd
import numpy as np
import pytest
import uuid
from src.services.profiling import ProfilingEngine

def test_profiling_engine_numeric(tmp_path):
    # Setup CSV file with outliers
    # Values: [-10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 20]
    # Q1=2.5, Q3=7.5, IQR=5.0, lower=-5.0, upper=15.0.
    # Outliers: 20, -10
    data = {
        "num_col": [1, 2, 3, 4, 5, 6, 7, 8, 9, 20, -10, None]
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / "test_numeric.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    
    assert profile["summary_metrics"]["row_count"] == 12
    assert profile["summary_metrics"]["column_count"] == 1
    assert profile["summary_metrics"]["missing_cells_count"] == 1
    
    col_meta = profile["columns_metadata"]["num_col"]
    assert col_meta["is_numeric"] is True
    assert col_meta["missing_count"] == 1
    assert col_meta["unique_count"] == 11
    assert col_meta["min"] == -10.0
    assert col_meta["max"] == 20.0
    assert col_meta["mean"] is not None
    assert col_meta["median"] == 5.0
    assert col_meta["outlier_count"] == 2 # -10 and 20

def test_profiling_engine_categorical(tmp_path):
    data = {
        "cat_col": ["apple", "banana", "apple", "cherry", None, "apple", "banana"]
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / "test_cat.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    
    col_meta = profile["columns_metadata"]["cat_col"]
    assert col_meta["is_numeric"] is False
    assert col_meta["missing_count"] == 1
    assert col_meta["unique_count"] == 3
    assert "apple" in col_meta["top_values"]
    assert col_meta["frequency_distribution"]["apple"] == 3
    assert col_meta["frequency_distribution"]["banana"] == 2

def test_profiling_engine_empty_numeric(tmp_path):
    data = {
        "empty_num": [None, None, None]
    }
    df = pd.DataFrame(data, dtype=float)
    file_path = str(tmp_path / "test_empty_num.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    col_meta = profile["columns_metadata"]["empty_num"]
    
    assert col_meta["is_numeric"] is True
    assert col_meta["min"] is None
    assert col_meta["outlier_count"] == 0

def test_profiling_engine_single_element_numeric(tmp_path):
    data = {
        "single_num": [10.0]
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / "test_single_num.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    col_meta = profile["columns_metadata"]["single_num"]
    
    assert col_meta["is_numeric"] is True
    assert col_meta["std"] == 0.0

def test_profiling_engine_duplicates(tmp_path):
    data = {
        "col1": [1, 2, 2, 3, 3, 3]
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / "test_dups.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    assert profile["summary_metrics"]["duplicate_rows_count"] == 3 # [2], [3], [3] duplicates
    
    # Let's make it completely unique by adding a unique column
    data = {
        "col1": [1, 2, 2, 3, 3, 3],
        "col2": [10, 20, 30, 40, 50, 60]
    }
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    profile = ProfilingEngine.profile(file_path, "text/csv")
    assert profile["summary_metrics"]["duplicate_rows_count"] == 0

def test_profiling_engine_outliers_edge(tmp_path):
    # Standard normal distribution without outliers
    data = {
        "col1": [10.0, 10.1, 10.2, 9.9, 9.8, 10.0, 10.1, 10.0, 9.9, 10.0]
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / "test_outliers_edge.csv")
    df.to_csv(file_path, index=False)

    profile = ProfilingEngine.profile(file_path, "text/csv")
    assert profile["columns_metadata"]["col1"]["outlier_count"] == 0

def test_validate_rules_disabled_rule():
    profile_result = {
        "summary_metrics": {
            "missing_cells_percent": 15.0,
            "duplicate_rows_percent": 0.0
        },
        "columns_metadata": {}
    }
    class MockRule:
        def __init__(self, id, name, rule_type, threshold, enabled):
            self.id = id
            self.rule_name = name
            self.rule_type = rule_type
            self.threshold = threshold
            self.enabled = enabled

    # Disabled rule: overall missing < 10% (would fail if enabled, but is disabled)
    rule = MockRule(uuid.uuid4(), "Test Disabled Rule", "NULL_PERCENT", 10.0, False)
    
    report = ProfilingEngine.validate_rules(profile_result, [rule])
    assert report["all_passed"] is True
    assert len(report["validations"]) == 0
