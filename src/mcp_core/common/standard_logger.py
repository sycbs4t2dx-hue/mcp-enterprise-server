"""
MCP系统标准日志配置
统一的日志格式和处理器
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # 格式化消息
        formatted = super().format(record)

        # 高亮特定模式
        patterns = {
            '✅': '\033[32m✅\033[0m',  # 成功
            '⚠️': '\033[33m⚠️\033[0m',   # 警告
            '❌': '\033[31m❌\033[0m',   # 错误
            '📊': '\033[34m📊\033[0m',  # 统计
            '🚀': '\033[36m🚀\033[0m',  # 启动
            '💾': '\033[35m💾\033[0m',  # 保存
        }

        for pattern, colored in patterns.items():
            formatted = formatted.replace(pattern, colored)

        return formatted


class StandardLogger:
    """标准日志配置器"""

    # 标准日志格式
    DEFAULT_FORMAT = '%(asctime)s [%(levelname)-8s] %(name)s - %(message)s'
    DETAILED_FORMAT = '%(asctime)s [%(levelname)-8s] %(name)s:%(funcName)s:%(lineno)d - %(message)s'
    JSON_FORMAT = '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","function":"%(funcName)s","line":%(lineno)d,"message":"%(message)s"}'

    # 日期格式
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(
        self,
        name: str = 'mcp',
        level: str = 'INFO',
        log_dir: str = 'logs',
        console: bool = True,
        file: bool = True,
        format_type: str = 'default'
    ):
        """
        初始化标准日志配置

        Args:
            name: 日志名称
            level: 日志级别
            log_dir: 日志目录
            console: 是否输出到控制台
            file: 是否输出到文件
            format_type: 格式类型 (default/detailed/json)
        """
        self.name = name
        self.level = getattr(logging, level.upper())
        self.log_dir = Path(log_dir)
        self.console = console
        self.file = file

        # 选择格式
        if format_type == 'detailed':
            self.format = self.DETAILED_FORMAT
        elif format_type == 'json':
            self.format = self.JSON_FORMAT
        else:
            self.format = self.DEFAULT_FORMAT

        # 创建日志目录
        if self.file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_logger(self, module_name: str = None) -> logging.Logger:
        """
        获取配置好的logger实例

        Args:
            module_name: 模块名称

        Returns:
            配置好的logger
        """
        logger_name = f"{self.name}.{module_name}" if module_name else self.name
        logger = logging.getLogger(logger_name)

        # 避免重复添加handler
        if logger.handlers:
            return logger

        logger.setLevel(self.level)
        logger.propagate = False

        # 控制台输出
        if self.console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)

            # 使用彩色格式化器
            if sys.stdout.isatty():  # 检查是否是终端
                console_formatter = ColoredFormatter(
                    self.format,
                    datefmt=self.DATE_FORMAT
                )
            else:
                console_formatter = logging.Formatter(
                    self.format,
                    datefmt=self.DATE_FORMAT
                )

            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # 文件输出
        if self.file:
            # 按日期轮转的文件handler
            log_file = self.log_dir / f"{self.name}.log"
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            file_handler.setLevel(self.level)

            file_formatter = logging.Formatter(
                self.format,
                datefmt=self.DATE_FORMAT
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # 错误日志单独记录
            if self.level <= logging.ERROR:
                error_file = self.log_dir / f"{self.name}_error.log"
                error_handler = logging.handlers.RotatingFileHandler(
                    error_file,
                    maxBytes=10485760,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(file_formatter)
                logger.addHandler(error_handler)

        return logger


# 全局日志配置实例
_standard_logger: Optional[StandardLogger] = None


def setup_logging(
    name: str = 'mcp',
    level: str = None,
    log_dir: str = 'logs',
    console: bool = True,
    file: bool = True,
    format_type: str = 'default'
) -> StandardLogger:
    """
    设置全局日志配置

    Args:
        name: 日志名称
        level: 日志级别（从环境变量或参数获取）
        log_dir: 日志目录
        console: 是否输出到控制台
        file: 是否输出到文件
        format_type: 格式类型

    Returns:
        StandardLogger实例
    """
    global _standard_logger

    # 从环境变量获取日志级别
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')

    _standard_logger = StandardLogger(
        name=name,
        level=level,
        log_dir=log_dir,
        console=console,
        file=file,
        format_type=format_type
    )

    return _standard_logger


def get_logger(module_name: str = None) -> logging.Logger:
    """
    获取logger实例

    Args:
        module_name: 模块名称，通常传入 __name__

    Returns:
        配置好的logger
    """
    global _standard_logger

    # 如果还没有初始化，使用默认配置
    if _standard_logger is None:
        setup_logging()

    return _standard_logger.get_logger(module_name)


# 日志级别辅助函数
def set_log_level(level: str):
    """动态设置日志级别"""
    if _standard_logger:
        new_level = getattr(logging, level.upper())
        for logger_name in logging.Logger.manager.loggerDict:
            if logger_name.startswith(_standard_logger.name):
                logger = logging.getLogger(logger_name)
                logger.setLevel(new_level)
                for handler in logger.handlers:
                    handler.setLevel(new_level)


# 结构化日志辅助函数
def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    带上下文的结构化日志

    Args:
        logger: logger实例
        level: 日志级别
        message: 日志消息
        **context: 上下文信息
    """
    extra = {'context': context} if context else {}
    getattr(logger, level.lower())(message, extra=extra)


# 性能日志装饰器
def log_performance(logger: logging.Logger = None):
    """
    记录函数性能的装饰器

    Args:
        logger: 指定的logger，如果没有则使用默认
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            start_time = time.time()
            logger.debug(f"Starting {func.__name__}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Completed {func.__name__} in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Failed {func.__name__} after {duration:.3f}s: {e}")
                raise

        return wrapper
    return decorator


# 使用示例和最佳实践
"""
使用示例：

1. 基本使用:
```python
from src.mcp_core.common.standard_logger import get_logger

logger = get_logger(__name__)
logger.info("服务启动")
logger.error("发生错误", exc_info=True)
```

2. 初始化配置:
```python
from src.mcp_core.common.standard_logger import setup_logging

# 在应用启动时配置
setup_logging(
    name='mcp',
    level='DEBUG',
    format_type='detailed'
)
```

3. 性能日志:
```python
from src.mcp_core.common.standard_logger import log_performance, get_logger

logger = get_logger(__name__)

@log_performance(logger)
def slow_function():
    time.sleep(1)
    return "done"
```

4. 结构化日志:
```python
from src.mcp_core.common.standard_logger import log_with_context

log_with_context(
    logger, 'info', '用户登录',
    user_id=123,
    ip='192.168.1.1',
    action='login'
)
```

最佳实践：
1. 始终使用 get_logger(__name__) 获取logger
2. 使用适当的日志级别：
   - DEBUG: 详细调试信息
   - INFO: 一般信息性消息
   - WARNING: 警告但不影响运行
   - ERROR: 错误但可以恢复
   - CRITICAL: 严重错误，可能导致程序终止
3. 包含足够的上下文信息
4. 避免在日志中暴露敏感信息
5. 使用结构化日志便于分析
"""