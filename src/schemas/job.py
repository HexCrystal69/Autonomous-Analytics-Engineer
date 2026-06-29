from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class ProfilingJobResponse(BaseModel):
    id: UUID
    dataset_version_id: UUID
    status: str
    task_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class DatasetProfileResponse(BaseModel):
    id: UUID
    dataset_version_id: UUID
    summary_metrics: Dict[str, Any]
    columns_metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
