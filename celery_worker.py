# celery_worker.py
import os
import sys
from app.celery_app import celery_app

if __name__ == "__main__":
    # 启动 Celery Worker
    from celery.bin import celery

    sys.argv = [
        "celery",
        "-A", "app.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=4",  # 并发数
        "-E"  # 启用事件
    ]

    celery.main()