from celery import Celery
from app.core.config import settings
import os

# 创建 Celery 应用
celery_app = Celery(
    "fastapi_rag_project",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.documents.documents_tasks"  # 文档处理任务
    ]  # 自动发现任务
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,  # 任务超时时间 30 分钟
    task_soft_time_limit=60 * 25,  # 任务软超时时间 25 分钟
    worker_prefetch_multiplier=1,  # 工作进程预取乘数, 每次只预取一个任务
    task_acks_late=True,  # 任务确认模式, 任务完成后才确认
    worker_max_tasks_per_child=100,  # 每个worker处理100个任务后重启
)

# 确保导入设置
celery_app.config_from_object("app.core.config", namespace="CELERY")

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])