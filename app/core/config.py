from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "FastAPI RAG Project"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # MySQL配置
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    # Milvus配置
    MILVUS_HOST: str
    MILVUS_PORT: int = 19530
    # 集合名（含混合检索 schema 的集合；旧集合 rag_collection 保留不破坏）
    MILVUS_COLLECTION: str = "rag_collection_v2"
    # 混合检索融合方式：rrf 或 weighted
    HYBRID_RANKER: str = "rrf"

    # 阿里云百炼配置
    ALIYUN_API_KEY: str
    ALIYUN_BASE_URL: str
    ALIYUN_MODEL: str = "deepseek-v4-flash"
    ALIYUN_EMBEDDING_MODEL: str = "text-embedding-v3"

    # Redis配置
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None  # 添加密码字段

    @property
    def REDIS_URL(self) -> str:
        """生成 Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # 使用 @property 或 @computed_field 动态生成URL
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        return f"mysql+asyncmy://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()