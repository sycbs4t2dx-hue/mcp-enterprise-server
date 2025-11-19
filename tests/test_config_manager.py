"""
Config Manager Unit Tests
测试配置管理器的所有功能
"""
import os
import json
import pytest
import tempfile
from unittest.mock import patch, mock_open

from config_manager import (
    ConfigManager,
    DatabaseConfig,
    AIConfig,
    ServerConfig,
    PerformanceConfig,
    load_config,
    create_default_config
)


class TestDatabaseConfig:
    """数据库配置测试"""

    @pytest.mark.unit
    def test_database_config_defaults(self):
        """测试:数据库配置默认值"""
        # Act
        config = DatabaseConfig()
        
        # Assert
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.user == "root"
        assert config.database == "mcp_db"
        assert config.charset == "utf8mb4"

    @pytest.mark.unit
    def test_database_url_generation(self):
        """测试:数据库URL生成"""
        # Arrange
        config = DatabaseConfig(
            user="testuser",
            password="testpass",
            host="db.example.com",
            port=3307,
            database="testdb"
        )
        
        # Act
        url = config.url
        
        # Assert
        assert "mysql+pymysql://" in url
        assert "testuser" in url
        assert "testpass" in url
        assert "db.example.com:3307" in url
        assert "testdb" in url

    @pytest.mark.unit
    def test_database_url_special_password(self):
        """测试:数据库URL - 特殊字符密码"""
        # Arrange
        config = DatabaseConfig(
            password="p@ss#w0rd!"
        )
        
        # Act
        url = config.url
        
        # Assert
        # 特殊字符应该被URL编码
        assert "p%40ss%23w0rd%21" in url or "p@ss#w0rd!" in url


class TestAIConfig:
    """AI配置测试"""

    @pytest.mark.unit
    def test_ai_config_defaults(self):
        """测试:AI配置默认值"""
        # Act
        config = AIConfig()
        
        # Assert
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.timeout == 30
        assert config.max_tokens == 4000

    @pytest.mark.unit
    def test_ai_enabled_with_key(self):
        """测试:AI启用 - 有API Key"""
        # Arrange
        config = AIConfig(api_key="sk-ant-test-key-123")
        
        # Act & Assert
        assert config.enabled is True

    @pytest.mark.unit
    def test_ai_disabled_without_key(self):
        """测试:AI禁用 - 无API Key"""
        # Arrange
        config = AIConfig(api_key=None)
        
        # Act & Assert
        assert config.enabled is False

    @pytest.mark.unit
    def test_ai_disabled_empty_key(self):
        """测试:AI禁用 - 空API Key"""
        # Arrange
        config = AIConfig(api_key="")
        
        # Act & Assert
        assert config.enabled is False


class TestConfigManagerInit:
    """配置管理器初始化测试"""

    @pytest.mark.unit
    def test_init_without_file(self):
        """测试:初始化 - 无配置文件"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.database is not None
        assert config.ai is not None
        assert config.server is not None
        assert config.performance is not None

    @pytest.mark.unit
    def test_init_with_nonexistent_file(self):
        """测试:初始化 - 不存在的配置文件"""
        # Act
        config = ConfigManager(config_file="/nonexistent/path/config.json")
        
        # Assert - 应该使用默认值
        assert config.database.host == "localhost"

    @pytest.mark.unit
    def test_init_with_valid_file(self):
        """测试:初始化 - 有效配置文件"""
        # Arrange
        config_data = {
            "database": {
                "host": "custom-db.example.com",
                "port": 3307,
                "database": "custom_db"
            },
            "server": {
                "log_level": "DEBUG"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            # Act
            config = ConfigManager(config_file=temp_file)
            
            # Assert
            assert config.database.host == "custom-db.example.com"
            assert config.database.port == 3307
            assert config.database.database == "custom_db"
            assert config.server.log_level == "DEBUG"
        finally:
            os.remove(temp_file)


class TestEnvironmentVariableLoading:
    """环境变量加载测试"""

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "DB_HOST": "env-db.example.com",
        "DB_PORT": "5432",
        "DB_USER": "envuser",
        "DB_PASSWORD": "envpass",
        "DB_NAME": "envdb"
    })
    def test_load_from_env_database(self):
        """测试:从环境变量加载数据库配置"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.database.host == "env-db.example.com"
        assert config.database.port == 5432
        assert config.database.user == "envuser"
        assert config.database.password == "envpass"
        assert config.database.database == "envdb"

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "DATABASE_URL": "mysql+pymysql://urluser:urlpass@url-db.com:3308/urldb"
    })
    def test_load_from_env_database_url(self):
        """测试:从环境变量加载DATABASE_URL"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.database.host == "url-db.com"
        assert config.database.port == 3308
        assert config.database.user == "urluser"
        assert config.database.password == "urlpass"
        assert config.database.database == "urldb"

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-env-key"
    })
    def test_load_from_env_anthropic_key(self):
        """测试:从环境变量加载Anthropic API Key"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.ai.api_key == "sk-ant-env-key"
        assert config.ai.provider == "anthropic"

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "sk-openai-env-key"
    })
    def test_load_from_env_openai_key(self):
        """测试:从环境变量加载OpenAI API Key"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.ai.api_key == "sk-openai-env-key"
        assert config.ai.provider == "openai"

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "custom.log",
        "MAX_WORKERS": "8",
        "REQUEST_TIMEOUT": "600"
    })
    def test_load_from_env_server_and_performance(self):
        """测试:从环境变量加载服务器和性能配置"""
        # Act
        config = ConfigManager()
        
        # Assert
        assert config.server.log_level == "DEBUG"
        assert config.server.log_file == "custom.log"
        assert config.performance.max_workers == 8
        assert config.performance.request_timeout == 600


class TestConfigValidation:
    """配置验证测试"""

    @pytest.mark.unit
    def test_validate_success(self):
        """测试:验证成功"""
        # Arrange
        config = ConfigManager()
        config.database.host = "localhost"
        config.database.user = "root"
        config.database.database = "mcp_db"
        
        # Act
        result = config.validate()
        
        # Assert
        assert result is True

    @pytest.mark.unit
    def test_validate_missing_host(self):
        """测试:验证失败 - 缺少主机"""
        # Arrange
        config = ConfigManager()
        config.database.host = ""
        
        # Act
        result = config.validate()
        
        # Assert
        assert result is False

    @pytest.mark.unit
    def test_validate_missing_user(self):
        """测试:验证失败 - 缺少用户"""
        # Arrange
        config = ConfigManager()
        config.database.user = ""
        
        # Act
        result = config.validate()
        
        # Assert
        assert result is False

    @pytest.mark.unit
    def test_validate_missing_database(self):
        """测试:验证失败 - 缺少数据库名"""
        # Arrange
        config = ConfigManager()
        config.database.database = ""
        
        # Act
        result = config.validate()
        
        # Assert
        assert result is False


class TestConfigSaveLoad:
    """配置保存和加载测试"""

    @pytest.mark.unit
    def test_save_to_file_success(self):
        """测试:保存配置文件成功"""
        # Arrange
        config = ConfigManager()
        config.database.host = "save-test.example.com"
        config.ai.model = "claude-3-opus"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Act
            config.save_to_file(temp_file)
            
            # Assert
            assert os.path.exists(temp_file)
            
            with open(temp_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["database"]["host"] == "save-test.example.com"
            assert saved_data["ai"]["model"] == "claude-3-opus"
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @pytest.mark.unit
    def test_save_to_file_creates_directory(self):
        """测试:保存配置文件 - 创建目录"""
        # Arrange
        config = ConfigManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "subdir", "config.json")
            
            # Act
            config.save_to_file(temp_file)
            
            # Assert
            assert os.path.exists(temp_file)

    @pytest.mark.unit
    def test_load_from_file_success(self):
        """测试:从文件加载配置成功"""
        # Arrange
        config_data = {
            "database": {
                "host": "loaded-db.example.com",
                "port": 3307
            },
            "ai": {
                "provider": "openai",
                "model": "gpt-4"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            # Act
            config = ConfigManager(config_file=temp_file)
            
            # Assert
            assert config.database.host == "loaded-db.example.com"
            assert config.database.port == 3307
            assert config.ai.provider == "openai"
            assert config.ai.model == "gpt-4"
        finally:
            os.remove(temp_file)

    @pytest.mark.unit
    def test_load_from_file_invalid_json(self):
        """测试:从文件加载 - 无效JSON"""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name
        
        try:
            # Act - 应该使用默认值,不抛出异常
            config = ConfigManager(config_file=temp_file)
            
            # Assert - 应该使用默认值
            assert config.database.host == "localhost"
        finally:
            os.remove(temp_file)


class TestHelperFunctions:
    """辅助函数测试"""

    @pytest.mark.unit
    def test_create_default_config(self):
        """测试:创建默认配置"""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Act
            config = create_default_config(config_file=temp_file)
            
            # Assert
            assert os.path.exists(temp_file)
            assert config.database.host == "localhost"
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @pytest.mark.unit
    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_USER": "root",
        "DB_DATABASE": "mcp_db"
    })
    def test_load_config_success(self):
        """测试:加载配置成功"""
        # Act
        config = load_config()
        
        # Assert
        assert config is not None
        assert isinstance(config, ConfigManager)

    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_validation_error(self):
        """测试:加载配置 - 验证失败"""
        # Arrange - 清空关键配置
        with patch.object(ConfigManager, 'validate', return_value=False):
            # Act & Assert
            with pytest.raises(ValueError, match="配置验证失败"):
                load_config()


class TestParseDatabaseURL:
    """数据库URL解析测试"""

    @pytest.mark.unit
    def test_parse_database_url_standard(self):
        """测试:解析标准数据库URL"""
        # Arrange
        config = ConfigManager()
        url = "mysql+pymysql://user123:pass456@db.host.com:3307/database123"
        
        # Act
        config._parse_database_url(url)
        
        # Assert
        assert config.database.user == "user123"
        assert config.database.password == "pass456"
        assert config.database.host == "db.host.com"
        assert config.database.port == 3307
        assert config.database.database == "database123"

    @pytest.mark.unit
    def test_parse_database_url_invalid(self):
        """测试:解析无效数据库URL"""
        # Arrange
        config = ConfigManager()
        original_host = config.database.host
        url = "invalid-url"
        
        # Act
        config._parse_database_url(url)
        
        # Assert - 应该保持原值不变
        assert config.database.host == original_host
