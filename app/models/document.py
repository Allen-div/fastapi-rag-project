from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), comment="文件路径")
    file_type = Column(String(50), comment="文件类型")
    file_size = Column(Integer, comment="文件大小")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    vector_id = Column(String(100), comment="向量ID")  # Milvus中的集合名
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, comment="状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    processed_at = Column(DateTime(timezone=True), nullable=True, comment="处理时间")
    celery_task_id = Column(String(100), nullable=True, comment="Celery任务ID")  # 存储 Celery 任务ID
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")