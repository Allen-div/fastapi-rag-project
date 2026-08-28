from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str  # user, assistant, tool
    content: str
    tool_calls: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int