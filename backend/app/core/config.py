from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path


def find_env_file():
    """查找.env文件"""
    # 当前目录
    current_dir = Path.cwd()
    env_path = current_dir / ".env"
    if env_path.exists():
        return str(env_path)
    
    # 上级目录
    parent_dir = current_dir.parent
    env_path = parent_dir / ".env"
    if env_path.exists():
        return str(env_path)
    
    # 项目根目录（通过查找特定文件判断）
    for parent in current_dir.parents:
        if (parent / "run.py").exists():
            env_path = parent / ".env"
            if env_path.exists():
                return str(env_path)
    
    return ".env"  # 默认值


class Settings(BaseSettings):
    # 硅基流动 API 配置
    SILICONFLOW_API_KEY: str
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # 向量数据库配置
    VECTORDB_TYPE: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./storage/chroma_db"
    
    # Embedding 配置
    EMBEDDING_PROVIDER: str = "siliconflow"
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    
    # LLM 配置
    LLM_PROVIDER: str = "siliconflow"
    LLM_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    RERANK_MODEL: str = "BAAI/bge-reranker-large"
    
    # JWT 配置
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 文件上传配置
    MAX_FILE_SIZE: str = "50MB"
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "docx", "pptx", "md", "txt"]
    STORAGE_DIR: str = "./storage"
    
    # RAG 配置
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    TOP_K: int = 12
    RERANK_TOP_N: int = 6
    CONFIDENCE_THRESHOLD: float = 0.45
    
    # 原子物理学科特定配置
    SUBJECT_NAME: str = "原子物理学"
    DEFAULT_COURSE_ID: str = "atomic_physics_2025"
    KNOWLEDGE_POINTS_FILE: str = "./data/atomic_physics_kp.json"
    
    # 性能配置
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 30
    EMBEDDING_BATCH_SIZE: int = 32
    VECTOR_SEARCH_TIMEOUT: int = 5
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_MAX_SIZE: str = "10MB"
    LOG_BACKUP_COUNT: int = 5
    
    class Config:
        env_file = find_env_file()
        case_sensitive = True
    
    def get_max_file_size_bytes(self) -> int:
        """转换文件大小字符串为字节数"""
        size_str = self.MAX_FILE_SIZE.upper()
        if size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        import os
        os.makedirs(self.STORAGE_DIR, exist_ok=True)
        os.makedirs(f"{self.STORAGE_DIR}/raw", exist_ok=True)
        os.makedirs(f"{self.STORAGE_DIR}/parsed", exist_ok=True)
        os.makedirs(self.CHROMA_PERSIST_DIR, exist_ok=True)
        os.makedirs("./logs", exist_ok=True)
        os.makedirs("./data", exist_ok=True)


settings = Settings()
settings.ensure_directories()