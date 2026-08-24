from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


# 对话表，相当于一个thread
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), default="新对话")
    thread_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
# cascade="all, delete-orphan"
#     这是级联操作配置，定义了当父对象（Conversation）发生变更时，对子对象（Message）的自动行为。
#     "all" 表示包括以下所有操作：
#     save-update：当父对象保存时，自动保存关联的子对象
#     merge：合并操作时级联
#     refresh-expire：刷新时级联
#     expunge：清除时级联
#     delete：当父对象删除时，同时删除所有关联的子对象
# "delete-orphan" 是额外行为：当一条 Message 不再属于任何 Conversation（即成为"孤儿"）时，自动删除它。


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")