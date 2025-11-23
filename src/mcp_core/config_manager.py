#!/usr/bin/env python3
"""
配置管理器

统一管理所有配置，支持环境变量、配置文件、默认值
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "mcp_db"
    charset: str = "utf8mb4"

    @property
    def url(self) -> str:
        """生成数据库URL"""
        # URL编码密码
        import urllib.parse
        password_encoded = urllib.parse.quote_plus(self.password)
        return f"mysql+pymysql://{self.user}:{password_encoded}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


@dataclass
class AIConfig:
    """AI服务配置"""
    provider: str = "anthropic"  # anthropic, openai
    api_key: Optional[str] = None
    model: str = "claude-3-5-sonnet-20241022"
    timeout: int = 30
    max_tokens: int = 4000

    @property
    def enabled(self) -> bool:
        """AI功能是否启用"""
        return self.api_key is not None and len(self.api_key) > 0


@dataclass
class ServerConfig:
    """服务器配置"""
    name: str = "mcp-unified-server"
    version: str = "2.0.0"
    protocol_version: str = "2024-11-05"
    log_level: str = "INFO"
    log_file: str = "logs/mcp_server.log"


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    request_timeout: int = 300  # 5分钟
    db_pool_size: int = 10
    db_max_overflow: int = 20


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径（可选）
        """
        self.config_file = config_file

        # 加载配置
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.server = ServerConfig()
        self.performance = PerformanceConfig()

        # 从环境变量加载
        self._load_from_env()

        # 从配置文件加载（如果提供）
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

    def _load_from_env(self):
        """从环境变量加载配置"""

        # 数据库配置
        if db_url := os.getenv("DATABASE_URL"):
            # 解析DATABASE_URL
            self._parse_database_url(db_url)
        else:
            self.database.host = os.getenv("DB_HOST", self.database.host)
            self.database.port = int(os.getenv("DB_PORT", self.database.port))
            self.database.user = os.getenv("DB_USER", self.database.user)
            self.database.password = os.getenv("DB_PASSWORD", self.database.password)
            self.database.database = os.getenv("DB_NAME", self.database.database)

        # AI配置
        self.ai.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        if openai_key := os.getenv("OPENAI_API_KEY"):
            self.ai.provider = "openai"
            self.ai.model = os.getenv("OPENAI_MODEL", "gpt-4")

        self.ai.model = os.getenv("AI_MODEL", self.ai.model)
        self.ai.timeout = int(os.getenv("AI_TIMEOUT", self.ai.timeout))

        # 服务器配置
        self.server.log_level = os.getenv("LOG_LEVEL", self.server.log_level)
        self.server.log_file = os.getenv("LOG_FILE", self.server.log_file)

        # 性能配置
        self.performance.max_workers = int(os.getenv("MAX_WORKERS", self.performance.max_workers))
        self.performance.request_timeout = int(os.getenv("REQUEST_TIMEOUT", self.performance.request_timeout))

    def _parse_database_url(self, url: str):
        """解析数据库URL"""
        # 简化版解析 mysql+pymysql://user:pass@host:port/db
        import re
        pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)'
        match = re.match(pattern, url)
        if match:
            self.database.user = match.group(1)
            self.database.password = match.group(2)
            self.database.host = match.group(3)
            self.database.port = int(match.group(4))
            self.database.database = match.group(5)

    def _load_from_file(self, config_file: str):
        """从配置文件加载"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # 更新数据库配置
            if "database" in config_data:
                db_config = config_data["database"]
                self.database.host = db_config.get("host", self.database.host)
                self.database.port = db_config.get("port", self.database.port)
                self.database.user = db_config.get("user", self.database.user)
                self.database.password = db_config.get("password", self.database.password)
                self.database.database = db_config.get("database", self.database.database)

            # 更新AI配置
            if "ai" in config_data:
                ai_config = config_data["ai"]
                self.ai.provider = ai_config.get("provider", self.ai.provider)
                self.ai.api_key = ai_config.get("api_key", self.ai.api_key)
                self.ai.model = ai_config.get("model", self.ai.model)

            # 更新服务器配置
            if "server" in config_data:
                server_config = config_data["server"]
                self.server.log_level = server_config.get("log_level", self.server.log_level)

        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}")

    def validate(self) -> bool:
        """验证配置"""
        errors = []

        # 验证数据库配置
        if not self.database.host:
            errors.append("数据库主机未配置")
        if not self.database.user:
            errors.append("数据库用户未配置")
        if not self.database.database:
            errors.append("数据库名称未配置")

        # 警告：AI未配置
        if not self.ai.enabled:
            print("⚠️  AI功能未启用（未配置API Key）")

        if errors:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def save_to_file(self, config_file: str):
        """保存配置到文件"""
        config_data = {
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "user": self.database.user,
                "password": self.database.password,
                "database": self.database.database
            },
            "ai": {
                "provider": self.ai.provider,
                "model": self.ai.model,
                "timeout": self.ai.timeout
            },
            "server": {
                "name": self.server.name,
                "version": self.server.version,
                "log_level": self.server.log_level
            },
            "performance": {
                "max_workers": self.performance.max_workers,
                "request_timeout": self.performance.request_timeout
            }
        }

        dir_name = os.path.dirname(config_file)
        if dir_name:  # 只有当目录路径不为空时才创建
            os.makedirs(dir_name, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

        print(f"✅ 配置已保存到: {config_file}")

    def print_summary(self):
        """打印配置摘要"""
        print("=" * 60)
        print(f"MCP服务器配置 - v{self.server.version}")
        print("=" * 60)

        print("\n📊 数据库:")
        print(f"  主机: {self.database.host}:{self.database.port}")
        print(f"  数据库: {self.database.database}")
        print(f"  用户: {self.database.user}")

        print("\n🤖 AI服务:")
        if self.ai.enabled:
            print(f"  提供商: {self.ai.provider}")
            print(f"  模型: {self.ai.model}")
            print(f"  状态: ✅ 已启用")
        else:
            print(f"  状态: ⚠️  未启用 (未配置API Key)")

        print("\n⚙️  服务器:")
        print(f"  名称: {self.server.name}")
        print(f"  版本: {self.server.version}")
        print(f"  日志级别: {self.server.log_level}")

        print("\n🚀 性能:")
        print(f"  最大工作线程: {self.performance.max_workers}")
        print(f"  请求超时: {self.performance.request_timeout}秒")
        print(f"  数据库连接池: {self.performance.db_pool_size}")

        print("=" * 60)


def create_default_config(config_file: str = "config/mcp_config.json"):
    """创建默认配置文件"""
    config = ConfigManager()
    config.save_to_file(config_file)
    return config


def load_config(config_file: Optional[str] = None) -> ConfigManager:
    """
    加载配置

    优先级: 环境变量 > 配置文件 > 默认值
    """
    # 如果未指定配置文件，尝试默认位置
    if not config_file:
        default_locations = [
            "config/mcp_config.json",
            "mcp_config.json",
            os.path.expanduser("~/.mcp/config.json")
        ]
        for location in default_locations:
            if os.path.exists(location):
                config_file = location
                break

    config = ConfigManager(config_file)

    # 验证配置
    if not config.validate():
        raise ValueError("配置验证失败，请检查配置")

    return config


# ==================== 测试代码 ====================

def test_config_manager():
    """测试配置管理器"""
    print("=" * 60)
    print("配置管理器测试")
    print("=" * 60)

    # 测试默认配置
    print("\n1. 加载默认配置:")
    config = ConfigManager()
    config.print_summary()

    # 测试保存和加载
    print("\n2. 保存配置文件:")
    test_file = "test_config.json"
    config.save_to_file(test_file)

    print("\n3. 从文件加载:")
    config2 = ConfigManager(test_file)
    print(f"  数据库URL: {config2.database.url}")

    # 清理
    if os.path.exists(test_file):
        os.remove(test_file)

    print("\n✅ 配置管理器测试完成")


if __name__ == "__main__":
    test_config_manager()
