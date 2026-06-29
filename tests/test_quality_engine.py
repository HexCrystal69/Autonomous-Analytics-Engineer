import pandas as pd
import pytest
import uuid
from src.services.quality_engine import QualityEngine

class MockRule:
    def __init__(self, id, name, rule_type, threshold, enabled=True):
        self.id = id
        self.rule_name = name
        self.rule_type = rule_type
        self.threshold = threshold
        self.enabled = enabled

def test_quality_engine_null_percentage():
    df = pd.DataFrame({"col1": [1, None, 3, None]}) # 2 out of 8 cells if 2 cols, here 1 col: 2/4 = 50% null
    rule = MockRule(uuid.uuid4(), "Null limit CRITICAL", "NULL_PERCENT", 30.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert violations[0]["severity"] == "critical"
    assert "null percent" in violations[0]["message"]

def test_quality_engine_duplicate_percentage():
    df = pd.DataFrame({"col1": [1, 1, 2, 2]}) # 2 duplicate rows out of 4 = 50% duplicate
    rule = MockRule(uuid.uuid4(), "Dup limit HIGH", "DUPLICATE_PERCENT", 40.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert violations[0]["severity"] == "high"

def test_quality_engine_col_null_percentage():
    df = pd.DataFrame({"col1": [1, None, None, 4]}) # 50% null in col1
    rule = MockRule(uuid.uuid4(), "Col Null limit MEDIUM", "COLUMN_NULL_PERCENT:col1", 30.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert violations[0]["severity"] == "medium"

def test_quality_engine_col_null_missing_col():
    df = pd.DataFrame({"col1": [1, 2]})
    rule = MockRule(uuid.uuid4(), "Col Null limit", "COLUMN_NULL_PERCENT:nonexistent", 30.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert "not found" in violations[0]["message"]

def test_quality_engine_range_min_max():
    df = pd.DataFrame({"age": [10, 25, 130]})
    rule_min = MockRule(uuid.uuid4(), "Min check", "COLUMN_MIN:age", 18.0)
    rule_max = MockRule(uuid.uuid4(), "Max check", "COLUMN_MAX:age", 120.0)
    violations = QualityEngine.validate(df, [rule_min, rule_max])
    assert len(violations) == 2

def test_quality_engine_regex_email():
    df = pd.DataFrame({"email": ["valid@test.com", "invalid-email", "test@domain.co.uk"]})
    # 1 invalid out of 3 = 33.3% failure rate. threshold = 10% allowed. So it fails.
    rule = MockRule(uuid.uuid4(), "Email check", "COLUMN_REGEX:email:EMAIL", 10.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert "regex mismatch" in violations[0]["message"]

def test_quality_engine_regex_phone():
    df = pd.DataFrame({"phone": ["+1234567890", "abc", "1234"]}) # abc is not phone
    rule = MockRule(uuid.uuid4(), "Phone check", "COLUMN_REGEX:phone:PHONE", 0.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1

def test_quality_engine_regex_zipcode():
    df = pd.DataFrame({"zip": ["12345", "12345-6789", "invalid"]})
    rule = MockRule(uuid.uuid4(), "Zip check", "COLUMN_REGEX:zip:ZIPCODE", 0.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1

def test_quality_engine_uniqueness():
    df = pd.DataFrame({"id": [1, 2, 2, 4]}) # 1 duplicate out of 4 = 25% duplication rate
    rule = MockRule(uuid.uuid4(), "Unique check", "COLUMN_UNIQUE:id", 10.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1

def test_quality_engine_disabled_rule():
    df = pd.DataFrame({"col1": [None, None]})
    rule = MockRule(uuid.uuid4(), "Null limit", "NULL_PERCENT", 10.0, enabled=False)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 0

def test_quality_engine_invalid_referential_definition():
    df = pd.DataFrame({"col1": [1, 2]})
    # Invalid format format (missing column link)
    rule = MockRule(uuid.uuid4(), "Bad Ref Rule", "REFERENTIAL:col1->baduuid", 0.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1
    assert "Invalid referential rule" in violations[0]["message"]

def test_quality_engine_range_boundaries_equal():
    df = pd.DataFrame({"val": [10.0, 10.0]})
    # Rule specifies min 10.0. Since values are exactly 10.0, they should pass.
    rule = MockRule(uuid.uuid4(), "Min limit", "COLUMN_MIN:val", 10.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 0

def test_quality_engine_empty_dataset_null_percent():
    df = pd.DataFrame()
    rule = MockRule(uuid.uuid4(), "Null limit", "NULL_PERCENT", 10.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 0

def test_quality_engine_uniqueness_on_mixed_types():
    df = pd.DataFrame({"id": ["a", 1, "a"]})
    rule = MockRule(uuid.uuid4(), "Unique Mixed", "COLUMN_UNIQUE:id", 0.0)
    violations = QualityEngine.validate(df, [rule])
    assert len(violations) == 1

