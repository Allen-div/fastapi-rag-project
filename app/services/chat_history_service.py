import uuid
from typing import List, Any, Sequence

from sqlalchemy import select, Row, RowMapping, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message


class ChatHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_conversations(self, user_id: int) -> Sequence[Conversation]:
        """获取用户的对话"""
        query = select(Conversation).where(Conversation.user_id == user_id)
        result = await self.db.execute(query)
        conversations = result.scalars().all()
        return conversations

    async def create_conversation(self, user_id: int, title: str) -> Conversation:
        """创建新对话"""
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            user_id=user_id,
            title=title,
            thread_id=thread_id
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_conversation_id(self, thread_id: str) -> int:
        """获取对话ID"""
        query = select(Conversation).where(Conversation.thread_id == thread_id)
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError("对话不存在")
        return conversation.id

    async def get_conversation_by_thread_id(self, thread_id: str) -> Conversation | None:
        """根据 thread_id 获取对话"""
        query = select(Conversation).where(Conversation.thread_id == thread_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        """保存消息"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def list_messages(self, conversation_id: int) -> Sequence[Message]:
        """按时间正序取出某会话的全部历史消息（供组装对话上下文，无 count 查询）"""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversations(self, user_id:int, page:int, page_size:int) -> tuple[
        Sequence[Conversation], int | None]:
        """获取对话列表"""
        query = select(Conversation).where(Conversation.user_id == user_id)
        query_count = select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        total_result = await self.db.execute(query_count)
        total = total_result.scalar()

        query = query.order_by(Conversation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        docs = result.scalars().all()
        return docs, total

    async def get_conversation(self, user_id:int, conversion_id:int) -> Conversation:
        """获取对话"""
        query = select(Conversation).filter(Conversation.id==conversion_id, Conversation.user_id==user_id)
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()
        return conversation


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_messages(self, conversation_id: int) -> tuple[
        Sequence[Message], int | None]:
        """获取某个对话消息历史"""
        query = select(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
        count_query = select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        result = await self.db.execute(query)
        messages = result.scalars().all()
        return messages, total

