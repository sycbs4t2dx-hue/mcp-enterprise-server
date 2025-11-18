"""
配置管理模块
支持多环境配置、热重载、环境变量覆盖
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    url: str = Field(default="mysql+pymysql://mcp_user:mcp_password@localhost:3306/mcp_db?charset=utf8mb4")
    pool_size: int = Field(default=20, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=50)
    pool_timeout: int = Field(default=30, ge=1)
    pool_recycle: int = Field(default=3600, ge=60)
    echo: bool = False


class RedisSettings(BaseSettings):
    """Redis配置"""

    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = Field(default=50, ge=1, le=500)
    socket_timeout: int = Field(default=5, ge=1)
    socket_connect_timeout: int = Field(default=5, ge=1)
    decode_responses: bool = False


class MilvusSettings(BaseSettings):
    """Milvus向量数据库配置"""

    host: str = "localhost"
    port: int = Field(default=19530, ge=1, le=65535)
    timeout: int = Field(default=30, ge=1)
    index_type: str = "HNSW"
    metric_type: str = "COSINE"
    index_params: Dict[str, int] = Field(default_factory=lambda: {"M": 16, "efConstruction": 200})
    search_params: Dict[str, int] = Field(default_factory=lambda: {"ef": 64})


class VectorDBSettings(BaseSettings):
    """向量数据库配置"""

    type: str = Field(default="milvus", pattern="^(milvus|faiss)$")
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    faiss_index_path: str = "./data/faiss_index"
    faiss_dimension: int = 768


class MemorySettings(BaseSettings):
    """记忆管理配置"""

    # 短期记忆
    short_term_ttl: int = Field(default=86400, ge=60)  # 最少1分钟
    short_term_max_window: int = Field(default=20, ge=1, le=100)
    short_term_min_window: int = Field(default=5, ge=1, le=20)

    # 中期记忆
    mid_term_ttl: int = Field(default=2592000, ge=3600)  # 最少1小时
    mid_term_auto_archive: bool = True
    mid_term_archive_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # 长期记忆
    long_term_min_confidence: float = Field(default=0.80, ge=0.0, le=1.0)

    # 检索配置
    retrieval_strategy: str = Field(default="hybrid", pattern="^(hybrid|semantic_only|keyword_only)$")
    default_top_k: int = Field(default=5, ge=1, le=50)
    max_top_k: int = Field(default=20, ge=1, le=100)
    cache_enabled: bool = True
    cache_ttl: int = Field(default=604800, ge=60)


class TokenOptimizationSettings(BaseSettings):
    """Token优化配置"""

    enabled: bool = True
    compression_ratio: float = Field(default=0.2, ge=0.1, le=0.9)
    cache_ttl: int = Field(default=604800, ge=60)

    # 模型配置
    code_model: str = "microsoft/codebert-base"
    text_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # 压缩策略
    compression_min_length: int = Field(default=200, ge=50)
    compression_max_length: int = Field(default=10000, ge=100)
    preserve_code_structure: bool = True


class AntiHallucinationSettings(BaseSettings):
    """幻觉抑制配置"""

    enabled: bool = True
    base_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

    # 自适应阈值
    adaptive_threshold_enabled: bool = True
    adaptive_min_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    adaptive_max_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    # 检测配置
    max_retries: int = Field(default=3, ge=1, le=10)
    timeout: int = Field(default=10, ge=1)
    enable_fact_check: bool = True

    # 告警配置
    alerts_enabled: bool = True
    alert_threshold: float = Field(default=0.10, ge=0.0, le=1.0)


class JWTSettings(BaseSettings):
    """JWT配置"""

    secret_key: str = Field(default="change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=1440, ge=1)  # 24小时

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """验证密钥强度"""
        if v == "change-this-in-production":
            import warnings

            warnings.warn("使用默认密钥不安全,请在生产环境修改!", UserWarning)
        if len(v) < 32:
            raise ValueError("JWT密钥长度必须≥32字符")
        return v


class SecuritySettings(BaseSettings):
    """安全配置"""

    jwt: JWTSettings = Field(default_factory=JWTSettings)
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = Field(default=90, ge=1)

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    cors_allow_credentials: bool = True

    # 速率限制
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = Field(default=100, ge=1)
    rate_limit_burst: int = Field(default=20, ge=1)


class LoggingSettings(BaseSettings):
    """日志配置"""

    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = Field(default="json", pattern="^(json|text)$")
    log_file: str = "./logs/mcp.log"
    max_bytes: int = Field(default=10485760, ge=1024)  # 10MB
    backup_count: int = Field(default=5, ge=1, le=20)
    mask_sensitive: bool = True


class MonitoringSettings(BaseSettings):
    """监控配置"""

    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = Field(default=9090, ge=1024, le=65535)
    metrics_prefix: str = "mcp"
    health_check_interval: int = Field(default=30, ge=1)


class APISettings(BaseSettings):
    """API配置"""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1024, le=65535)
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"])
    workers: int = Field(default=4, ge=1, le=32)


class AppSettings(BaseSettings):
    """应用配置"""

    debug: bool = False
    name: str = "MCP"
    version: str = "1.0.0"
    environment: str = Field(default="development", pattern="^(development|testing|production)$")


class Settings(BaseSettings):
    """主配置类"""

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # 项目基础配置
    project_name: str = "mcp-core"
    project_version: str = "1.0.0"
    environment: str = Field(default="development", pattern="^(development|testing|production)$")

    # 应用配置
    app: AppSettings = Field(default_factory=AppSettings)
    api: APISettings = Field(default_factory=APISettings)

    # 服务配置
    server_host: str = "0.0.0.0"
    server_port: int = Field(default=8000, ge=1024, le=65535)
    server_workers: int = Field(default=4, ge=1, le=32)
    server_reload: bool = True

    # 各模块配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    token_optimization: TokenOptimizationSettings = Field(default_factory=TokenOptimizationSettings)
    anti_hallucination: AntiHallucinationSettings = Field(
        default_factory=AntiHallucinationSettings
    )
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Settings":
        """从YAML文件加载配置"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 直接使用嵌套配置，不需要扁平化
        # Pydantic会自动处理嵌套结构
        return cls(**config_data)

    @staticmethod
    def _flatten_config(config: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items: List[tuple] = []

        for k, v in config.items():
            new_key = f"{parent_key}_{k}" if parent_key else k

            if isinstance(v, dict) and not k.endswith("_params"):  # 保留params字典
                items.extend(Settings._flatten_config(v, new_key).items())
            else:
                items.append((new_key, v))

        return dict(items)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例(带缓存)"""
    config_path = os.getenv("MCP_CONFIG_PATH", "config.yaml")

    if Path(config_path).exists():
        return Settings.from_yaml(config_path)
    else:
        # 使用默认配置
        return Settings()


def load_config(config_path: Optional[str] = None) -> Settings:
    """加载配置(不带缓存,用于测试)"""
    if config_path:
        return Settings.from_yaml(config_path)
    return Settings()


# 便捷访问
settings = get_settings()
