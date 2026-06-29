from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class DatasetVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    version_number: int
    filename: str
    mime_type: str
    file_size: int
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DatasetResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    versions: List[DatasetVersionResponse] = []

    class Config:
        from_attributes = True

class DatasetListResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    latest_version: Optional[DatasetVersionResponse] = None

    class Config:
        from_attributes = True
