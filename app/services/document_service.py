import os
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func

from app.core.logging import logger
from app.models import Document
from app.models.document import DocumentStatus
from app.services.vector_service import VectorService


class DocumentService:
    def __init__(self, db):
        self.db=db

    async def create_document(self, user_id: int, file_name: str, file_path: str, file_ext: str, file_size: int, status: DocumentStatus):
        # 保存到mysql
        doc = Document(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_size,
            status=status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(doc)

        try:
            await self.db.commit()
            await self.db.refresh(doc)
            return doc
        except Exception as e:
            await self.db.rollback()
            raise ValueError(e)

    async def list_user_documents(self, user_id: int, page: int, page_size: int) -> tuple[Sequence[Document], int]:
        """查询用户上传的文件。

        注意：MySQL 5.7 不支持窗口函数（COUNT(*) OVER()），因此 count 与分页需分开查询。
        认证环节已改为免查库（JWT 直取），整体仍比原始实现少一次往返。
        """
        count_stmt = select(func.count()).select_from(Document).where(Document.user_id == user_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        query = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        docs = result.scalars().all()
        return docs, total

    async def delete_document(self, userid: int, document_id: int):
        """删除文档"""
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"文档: id={document_id}不存在")
        if document.user_id != userid:
            raise ValueError(f"文档: user_id={document.user_id}, {userid}没有权限删除")

        # 如果任务还在运行，尝试撤销（terminate=False 只撤销队列中未开始的任务，
        # 不强制终止整个 worker 进程，避免杀掉同 worker 上的其他任务）
        if document.celery_task_id:
            try:
                from app.tasks.documents.documents_tasks import process_document
                process_document.AsyncResult(document.celery_task_id).revoke(terminate=False)
            except Exception as e:
                logger.warning(f"撤销 Celery 任务失败: {document.celery_task_id}, error={e}")

        # 删除本地文件
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {document.file_path}, error={e}")

        # 删除向量数据库中的数据（VectorService 为全局单例，懒连接）
        if document.vector_id:
            try:
                VectorService().delete_by_doc_id(document.vector_id)
            except Exception as e:
                logger.warning(f"删除向量失败: {document.vector_id}, error={e}")

        # 从mysql删除
        await self.db.delete(document)
        await self.db.commit()
