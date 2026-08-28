from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,     # 生产环境建议设为 False
    pool_size=10,            # 连接池大小
    max_overflow=20          # 连接池溢出容量
)

# 创建异步会话工厂
# 利用 async_sessionmaker 管理会话：结合 FastAPI 的依赖注入系统，实现会话的自动获取与释放
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不自动过期对象
    autocommit=False,
    autoflush=False
)

# 所有模型的基类
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # 在 FastAPI 的上下文中，'async with' 块结束后会话会自动关闭
            # 这里的 finally 确保了即使发生异常，会话也能被正确清理
            await session.close()