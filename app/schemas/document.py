from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    doc_id: str
    file_name: str
    chunk_count: int


class DocumentResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    chunk_count: int
    vector_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

