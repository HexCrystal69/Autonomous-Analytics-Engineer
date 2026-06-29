from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any

class DataQualityRuleCreate(BaseModel):
    rule_name: str
    rule_type: str  # NULL_PERCENT, DUPLICATE_PERCENT, COLUMN_NULL_PERCENT:col, COLUMN_MIN:col, COLUMN_MAX:col
    threshold: float
    enabled: bool = True

class DataQualityRuleResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    rule_name: str
    rule_type: str
    threshold: float
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True

class RuleValidationItem(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str
    threshold: float
    actual_value: Optional[float] = None
    passed: bool
    error_message: str

class ValidationResultResponse(BaseModel):
    all_passed: bool
    validations: List[RuleValidationItem]
