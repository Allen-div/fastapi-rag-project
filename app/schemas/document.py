from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    doc_id: int
    file_name: str
    file_size: int
    status: Optional[str] = None
    task_id: Optional[str] = None
    message: str


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    chunk_count: Optional[int] = None
    vector_id: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

