"""
文档处理任务
"""

import asyncio

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.celery_app import celery_app
from app.core.config import settings
from app.models.document import DocumentStatus
from app.utils.document_utils import update_document_status, process_document_async


@celery_app.task(bind=True, name="document_process")
def process_document(self: Task, document_id: int, file_path: str, file_type: str, user_id: int):
    """
    文档处理任务
    :param self: Task
    :param document_id: 文档ID
    :param file_path: 文件路径
    :param file_type: 文件类型
    :param user_id: 用户ID
    :return: 处理结果

    注意：
    1. Celery prefork worker 无法直接运行 async def 任务（协程不会被 await，
       会被当作结果序列化导致 EncodeError），因此这里用同步函数包装 + asyncio.run。
    2. asyncio.run 每次会新建事件循环，所以每个任务必须使用绑定当前循环的独立 engine
       （NullPool，不跨循环复用连接），否则复用全局连接池会报
       "Future attached to a different loop" 错误。
    """
    async def _run():
        # 为当前事件循环创建独立 engine（NullPool：不缓存连接，避免跨循环复用）
        engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            poolclass=NullPool,
        )
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        try:
            async with session_factory() as db:
                await process_document_async(
                    document_id, file_path, file_type, user_id, self.request.id, db=db
                )
        except Exception as e:
            # 用全新的 session 更新失败状态，避免复用已处于异常事务中的 session
            try:
                async with session_factory() as db:
                    await update_document_status(
                        document_id, DocumentStatus.FAILED, error_message=str(e), db=db
                    )
            except Exception as update_error:
                self.logger.error(f"更新文档失败状态异常: document_id={document_id}, error={update_error}")
            raise e
        finally:
            await engine.dispose()

    return asyncio.run(_run())
