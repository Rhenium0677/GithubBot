"""
应用配置模块
负责从环境变量加载和管理所有配置信息
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 文件路径
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.is_file():
    load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """应用配置模型"""
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore' # Ignore extra fields from environment
    )

    # --- 应用基本配置 ---
    APP_NAME: str = "GithubBot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_KEY: Optional[str] = None
    CORS_ORIGINS: str = ""

    @field_validator("CORS_ORIGINS", mode='after')
    def parse_cors_origins(cls, v: str) -> List[str]:
        """解析 CORS_ORIGINS 字符串为 URL 列表"""
        if not v:
            return []

        # 去除可能的引号
        v = v.strip().strip("'\"")

        # 如果是 JSON 数组格式
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(url).strip() for url in parsed if url]
            except json.JSONDecodeError:
                pass

        # 否则作为逗号分隔的字符串处理
        return [url.strip() for url in v.split(",") if url.strip()]

    # --- 服务端口配置 ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # --- 数据库配置 (PostgreSQL) ---
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "repoinsight"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode='before')
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        return (
            f"postgresql+psycopg2://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}"
            f"@{values.get('POSTGRES_HOST')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )

    # --- 消息队列配置 (Redis) ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode='before')
    def assemble_redis_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        values = info.data
        return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB', 0)}"

    # --- Celery 配置 ---
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_RESULT_EXPIRES: int = 3600

    @field_validator("CELERY_BROKER_URL", mode='before')
    def set_celery_broker(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        # 使用 REDIS_URL 作为 Celery broker
        values = info.data
        redis_url = values.get('REDIS_URL')
        if not redis_url:
            return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB', 0)}"
        return redis_url

    @field_validator("CELERY_RESULT_BACKEND", mode='before')
    def set_celery_backend(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        # 使用 REDIS_URL 作为 Celery result backend
        values = info.data
        redis_url = values.get('REDIS_URL')
        if not redis_url:
            return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB', 0)}"
        return redis_url

    # --- 向量数据库配置 (ChromaDB) ---
    # 本地持久化路径。如果设置此项，将优先使用本地存储，并忽略下面的 HOST/PORT 配置。
    # 例如: CHROMADB_PERSISTENT_PATH="./chroma_data"
    CHROMADB_PERSISTENT_PATH: Optional[str] = None

    # 远程 ChromaDB 服务器配置 (当 CHROMADB_PERSISTENT_PATH 未设置时使用)
    CHROMADB_HOST: str = "chromadb"
    CHROMADB_PORT: int = 8000

    # --- LLM 和 Embedding 模型 API Keys ---
    OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    HUGGINGFACE_HUB_API_TOKEN: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None

    # --- Git 配置 ---
    GIT_CLONE_DIR: str = "/repo_clones"
    CLONE_TIMEOUT: int = 300

    # --- 索引和嵌入配置（默认） ---
    EMBEDDING_BATCH_SIZE: int = 32
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # 默认允许处理的文件扩展名列表 (逗号分隔)
    ALLOWED_FILE_EXTENSIONS: str = (
        ".py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.hpp,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,"
        ".md,.txt,.rst,.json,.yaml,.yml,.toml,.ini,.cfg,.sh,.sql,.html,.css,.vue,"
        "dockerfile,makefile,readme,license,changelog"
    )

    # 默认排除的目录列表 (逗号分隔)
    EXCLUDED_DIRECTORIES: str = ".git,node_modules,dist,build,venv,.venv,target"

    @field_validator("ALLOWED_FILE_EXTENSIONS", "EXCLUDED_DIRECTORIES", mode='before')
    def parse_comma_separated_string(cls, v: str) -> List[str]:
        """将逗号分隔的字符串解析为列表"""
        if not v:
            return []
        return [item.strip() for item in v.split(',') if item.strip()]

    #---混合检索返回的文件个数---
    FINAL_CONTEXT_TOP_K: int = 5

    # --- 向量检索和 BM25 检索返回的文档数量 ---
    VECTOR_SEARCH_TOP_K: int = 10
    BM25_SEARCH_TOP_K: int = 10

# 全局配置实例
settings = Settings()


# 日志设置
def setup_logging():
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # 可以为特定的库设置不同的日志级别
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def validate_config():
    """在应用启动时验证关键配置"""
    if settings.API_KEY:
        logging.info("API Key 已配置。")
    else:
        logging.warning("警告: API_KEY 未设置，API 将无保护。")