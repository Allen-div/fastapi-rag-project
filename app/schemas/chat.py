from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    top_k: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    thread_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
