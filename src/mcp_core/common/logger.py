"""
日志管理模块
支持JSON格式、敏感信息过滤、多Handler
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_settings


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""

    SENSITIVE_FIELDS = ["password", "token", "api_key", "secret", "authorization"]

    def __init__(self, mask_sensitive: bool = True):
        super().__init__()
        self.mask_sensitive = mask_sensitive

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤敏感信息"""
        if not self.mask_sensitive:
            return True

        # 过滤消息
        if isinstance(record.msg, str):
            record.msg = self._mask_string(record.msg)

        # 过滤额外字段
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            record.extra = self._mask_dict(record.extra)

        return True

    def _mask_string(self, text: str) -> str:
        """遮蔽字符串中的敏感信息"""
        for field in self.SENSITIVE_FIELDS:
            if field in text.lower():
                # 简化处理:遮蔽引号内的值
                import re

                pattern = f'{field}["\']?\\s*[:=]\\s*["\']?([^"\'\\s,}}]+)'
                text = re.sub(pattern, f'{field}="***MASKED***"', text, flags=re.IGNORECASE)

        return text

    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """遮蔽字典中的敏感信息"""
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked[key] = self._mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    self._mask_dict(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                masked[key] = value
        return masked


class JSONFormatter(logging.Formatter):
    """JSON格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志为JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加自定义字段
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data["extra"] = record.extra

        # 添加请求ID(如果存在)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data, ensure_ascii=False)


class ColoredTextFormatter(logging.Formatter):
    """彩色文本格式化器(用于控制台)"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志为彩色文本"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        formatted = super().format(record)
        return formatted


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别
        log_format: 日志格式(json/text)
        log_file: 日志文件路径
    """
    settings = get_settings()

    # 使用配置或参数
    level = log_level or settings.logging.level
    format_type = log_format or settings.logging.format
    file_path = log_file or settings.logging.log_file

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 清除已有handlers
    root_logger.handlers.clear()

    # 添加控制台Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if format_type == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_formatter = ColoredTextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)

    # 添加敏感数据过滤器
    if settings.logging.mask_sensitive:
        console_handler.addFilter(SensitiveDataFilter(mask_sensitive=True))

    root_logger.addHandler(console_handler)

    # 添加文件Handler
    if file_path:
        # 确保日志目录存在
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=settings.logging.max_bytes,
            backupCount=settings.logging.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)

        # 文件日志统一使用JSON格式
        file_handler.setFormatter(JSONFormatter())

        if settings.logging.mask_sensitive:
            file_handler.addFilter(SensitiveDataFilter(mask_sensitive=True))

        root_logger.addHandler(file_handler)

    # 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称

    Returns:
        logging.Logger实例
    """
    return logging.getLogger(name)


# 便捷日志函数
class LoggerAdapter(logging.LoggerAdapter):
    """日志适配器,支持附加上下文"""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """处理日志消息"""
        # 将extra字段传递给记录器
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # 添加适配器的extra
        if self.extra:
            kwargs["extra"].update(self.extra)

        return msg, kwargs


def get_context_logger(name: str, **context: Any) -> LoggerAdapter:
    """
    获取带上下文的日志器

    Args:
        name: 日志器名称
        **context: 上下文字段

    Returns:
        LoggerAdapter实例

    Example:
        logger = get_context_logger("mcp.api", user_id="user_001", request_id="req_123")
        logger.info("API called")
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, {"extra": context})


# 初始化日志(导入时自动执行)
setup_logging()
