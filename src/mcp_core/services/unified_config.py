"""
统一配置管理器
支持多源配置、热重载、环境变量覆盖
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..common.logger import get_logger

logger = get_logger(__name__)


class ConfigSource(Enum):
    """配置源类型"""
    FILE = "file"           # 文件（YAML/JSON）
    ENV = "environment"     # 环境变量
    REMOTE = "remote"       # 远程配置中心
    DEFAULT = "default"     # 默认值


@dataclass
class ConfigSchema:
    """配置模式定义"""

    @dataclass
    class Database:
        url: str = "mysql+pymysql://root:password@localhost:3306/mcp_db"
        pool_size: int = 20
        max_overflow: int = 10
        pool_timeout: int = 30
        pool_recycle: int = 3600
        echo: bool = False

    @dataclass
    class Redis:
        host: str = "localhost"
        port: int = 6379
        db: int = 0
        password: Optional[str] = None
        timeout: int = 5
        max_connections: int = 50

    @dataclass
    class Milvus:
        host: str = "localhost"
        port: int = 19530
        timeout: int = 30
        index_type: str = "HNSW"
        metric_type: str = "COSINE"

    @dataclass
    class Cache:
        l1_capacity: int = 2000
        l1_ttl: int = 60
        l2_ttl: int = 300
        enabled: bool = True

    @dataclass
    class WebSocket:
        host: str = "0.0.0.0"
        port: int = 8765
        max_connections: int = 1000
        heartbeat_interval: int = 30

    @dataclass
    class API:
        rate_limit: int = 100
        rate_limit_window: int = 60
        cors_enabled: bool = True
        api_keys: List[str] = field(default_factory=list)
        allowed_ips: List[str] = field(default_factory=list)

    @dataclass
    class Logging:
        level: str = "INFO"
        format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        file: Optional[str] = None
        max_bytes: int = 10485760  # 10MB
        backup_count: int = 5

    @dataclass
    class Performance:
        enable_profiling: bool = False
        enable_metrics: bool = True
        metrics_port: int = 9090

    # 主配置
    database: Database = field(default_factory=Database)
    redis: Redis = field(default_factory=Redis)
    milvus: Milvus = field(default_factory=Milvus)
    cache: Cache = field(default_factory=Cache)
    websocket: WebSocket = field(default_factory=WebSocket)
    api: API = field(default_factory=API)
    logging: Logging = field(default_factory=Logging)
    performance: Performance = field(default_factory=Performance)


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监视器"""

    def __init__(self, config_manager: 'UnifiedConfigManager'):
        self.config_manager = config_manager
        self.last_modified = {}

    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent):
            return

        # 防抖处理（1秒内的重复事件忽略）
        file_path = event.src_path
        current_time = time.time()

        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < 1:
                return

        self.last_modified[file_path] = current_time

        # 触发重载
        if file_path.endswith(('.yaml', '.yml', '.json')):
            logger.info(f"配置文件变更检测: {file_path}")
            self.config_manager._trigger_reload(file_path)


class UnifiedConfigManager:
    """
    统一配置管理器

    特性：
    - 多源配置合并
    - 环境变量覆盖
    - 热重载支持
    - 配置验证
    - 变更通知
    """

    def __init__(self, config_files: Optional[List[str]] = None):
        """
        初始化配置管理器

        Args:
            config_files: 配置文件列表（按优先级排序）
        """
        self.config_files = config_files or ["config.yaml", "config.local.yaml"]
        self.config = ConfigSchema()
        self._raw_config = {}
        self._observers = []
        self._change_callbacks = []
        self._lock = threading.RLock()

        # 文件监视器
        self._file_observer = None
        self._watcher = None

        # 加载配置
        self._load_all_configs()

        # 启动热重载（如果启用）
        if os.getenv("CONFIG_HOT_RELOAD", "false").lower() == "true":
            self._start_file_watcher()

        logger.info("统一配置管理器初始化完成")

    def _load_all_configs(self):
        """加载所有配置源"""
        with self._lock:
            # 1. 加载默认配置
            self._raw_config = asdict(ConfigSchema())

            # 2. 加载配置文件
            for config_file in self.config_files:
                self._load_config_file(config_file)

            # 3. 应用环境变量覆盖
            self._apply_env_overrides()

            # 4. 构建配置对象
            self._build_config_object()

            # 5. 验证配置
            self._validate_config()

    def _load_config_file(self, file_path: str):
        """加载单个配置文件"""
        path = Path(file_path)
        if not path.exists():
            logger.debug(f"配置文件不存在: {file_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f) or {}
                elif path.suffix == '.json':
                    file_config = json.load(f)
                else:
                    logger.warning(f"不支持的配置文件类型: {file_path}")
                    return

            # 深度合并配置
            self._deep_merge(self._raw_config, file_config)
            logger.info(f"加载配置文件: {file_path}")

        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 数据库配置
        if db_url := os.getenv("DATABASE_URL"):
            self._raw_config.setdefault("database", {})["url"] = db_url

        if db_password := os.getenv("DB_PASSWORD"):
            # 替换URL中的密码
            if "database" in self._raw_config and "url" in self._raw_config["database"]:
                url = self._raw_config["database"]["url"]
                # 简单的密码替换逻辑
                if "password@" in url:
                    parts = url.split("password@")
                    self._raw_config["database"]["url"] = f"{parts[0]}{db_password}@{parts[1]}"

        # Redis配置
        if redis_host := os.getenv("REDIS_HOST"):
            self._raw_config.setdefault("redis", {})["host"] = redis_host

        if redis_port := os.getenv("REDIS_PORT"):
            self._raw_config.setdefault("redis", {})["port"] = int(redis_port)

        if redis_password := os.getenv("REDIS_PASSWORD"):
            self._raw_config.setdefault("redis", {})["password"] = redis_password

        # Milvus配置
        if milvus_host := os.getenv("MILVUS_HOST"):
            self._raw_config.setdefault("milvus", {})["host"] = milvus_host

        if milvus_port := os.getenv("MILVUS_PORT"):
            self._raw_config.setdefault("milvus", {})["port"] = int(milvus_port)

        # API配置
        if api_keys := os.getenv("API_KEYS"):
            self._raw_config.setdefault("api", {})["api_keys"] = api_keys.split(",")

        # 日志级别
        if log_level := os.getenv("LOG_LEVEL"):
            self._raw_config.setdefault("logging", {})["level"] = log_level

    def _build_config_object(self):
        """构建配置对象"""
        try:
            # 创建各个子配置
            self.config = ConfigSchema(
                database=ConfigSchema.Database(**self._raw_config.get("database", {})),
                redis=ConfigSchema.Redis(**self._raw_config.get("redis", {})),
                milvus=ConfigSchema.Milvus(**self._raw_config.get("milvus", {})),
                cache=ConfigSchema.Cache(**self._raw_config.get("cache", {})),
                websocket=ConfigSchema.WebSocket(**self._raw_config.get("websocket", {})),
                api=ConfigSchema.API(**self._raw_config.get("api", {})),
                logging=ConfigSchema.Logging(**self._raw_config.get("logging", {})),
                performance=ConfigSchema.Performance(**self._raw_config.get("performance", {}))
            )
        except Exception as e:
            logger.error(f"构建配置对象失败: {e}")
            # 使用默认配置
            self.config = ConfigSchema()

    def _validate_config(self):
        """验证配置"""
        errors = []

        # 验证数据库URL
        if not self.config.database.url:
            errors.append("数据库URL未配置")

        # 验证端口范围
        if not (0 < self.config.redis.port < 65536):
            errors.append(f"Redis端口无效: {self.config.redis.port}")

        if not (0 < self.config.milvus.port < 65536):
            errors.append(f"Milvus端口无效: {self.config.milvus.port}")

        # 验证缓存配置
        if self.config.cache.l1_capacity <= 0:
            errors.append(f"L1缓存容量无效: {self.config.cache.l1_capacity}")

        if errors:
            for error in errors:
                logger.warning(f"配置验证警告: {error}")

    def _start_file_watcher(self):
        """启动文件监视器"""
        try:
            self._watcher = ConfigFileWatcher(self)
            self._file_observer = Observer()

            # 监视配置文件
            for config_file in self.config_files:
                path = Path(config_file)
                if path.exists():
                    self._file_observer.schedule(
                        self._watcher,
                        str(path.parent),
                        recursive=False
                    )

            self._file_observer.start()
            logger.info("配置文件热重载已启用")

        except Exception as e:
            logger.error(f"启动文件监视器失败: {e}")

    def _trigger_reload(self, file_path: str):
        """触发配置重载"""
        logger.info(f"触发配置重载: {file_path}")

        # 备份当前配置
        old_config = self._raw_config.copy()

        try:
            # 重新加载配置
            self._load_all_configs()

            # 通知所有观察者
            self._notify_changes(old_config, self._raw_config)

            logger.info("配置重载成功")

        except Exception as e:
            logger.error(f"配置重载失败: {e}")
            # 恢复旧配置
            self._raw_config = old_config
            self._build_config_object()

    def _notify_changes(self, old_config: Dict, new_config: Dict):
        """通知配置变更"""
        changes = self._find_changes(old_config, new_config)

        if changes:
            logger.info(f"配置变更: {changes}")

            for callback in self._change_callbacks:
                try:
                    callback(changes)
                except Exception as e:
                    logger.error(f"配置变更回调失败: {e}")

    def _find_changes(self, old: Dict, new: Dict, path: str = "") -> Dict:
        """查找配置变更"""
        changes = {}

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in old:
                changes[current_path] = {"action": "added", "value": new[key]}
            elif key not in new:
                changes[current_path] = {"action": "removed", "old_value": old[key]}
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    nested_changes = self._find_changes(old[key], new[key], current_path)
                    changes.update(nested_changes)
                else:
                    changes[current_path] = {
                        "action": "modified",
                        "old_value": old[key],
                        "new_value": new[key]
                    }

        return changes

    def register_change_callback(self, callback: Callable[[Dict], None]):
        """注册配置变更回调"""
        self._change_callbacks.append(callback)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        keys = key.split(".")
        value = self._raw_config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置值（仅内存，不持久化）"""
        with self._lock:
            keys = key.split(".")
            config = self._raw_config

            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            config[keys[-1]] = value

            # 重建配置对象
            self._build_config_object()

    def export(self, format: str = "yaml") -> str:
        """导出配置"""
        if format == "yaml":
            return yaml.dump(self._raw_config, default_flow_style=False)
        elif format == "json":
            return json.dumps(self._raw_config, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def reload(self):
        """手动重载配置"""
        self._load_all_configs()
        logger.info("配置手动重载完成")

    def stop(self):
        """停止配置管理器"""
        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join()
            logger.info("文件监视器已停止")


# 全局配置实例
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager() -> UnifiedConfigManager:
    """获取配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
    return _config_manager


def get_config() -> ConfigSchema:
    """获取配置对象"""
    return get_config_manager().config


# 便捷函数
def config_get(key: str, default: Any = None) -> Any:
    """快速获取配置值"""
    return get_config_manager().get(key, default)


def config_set(key: str, value: Any):
    """快速设置配置值"""
    get_config_manager().set(key, value)