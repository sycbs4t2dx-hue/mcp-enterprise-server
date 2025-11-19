"""
Redis Client Unit Tests
测试Redis客户端的所有功能
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.mcp_core.services.redis_client import RedisClient, get_redis_client


class TestRedisClientInit:
    """Redis客户端初始化测试"""

    @pytest.mark.unit
    @patch('src.mcp_core.services.redis_client.redis.Redis')
    @patch('src.mcp_core.services.redis_client.ConnectionPool')
    def test_init_success(self, mock_pool, mock_redis):
        """测试:初始化成功"""
        # Arrange
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True

        # Act
        client = RedisClient(redis_url="redis://localhost:6379/1")

        # Assert
        assert client is not None
        mock_redis_instance.ping.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.redis_client.redis.Redis')
    @patch('src.mcp_core.services.redis_client.ConnectionPool')
    def test_init_connection_error(self, mock_pool, mock_redis):
        """测试:初始化失败 - 连接错误"""
        # Arrange
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        import redis as redis_lib
        mock_redis_instance.ping.side_effect = redis_lib.ConnectionError("Connection refused")

        # Act & Assert
        with pytest.raises(redis_lib.ConnectionError):
            RedisClient(redis_url="redis://invalid:6379/1")

    @pytest.mark.unit
    def test_mask_url(self):
        """测试:URL密码遮蔽"""
        # Arrange
        client = RedisClient.__new__(RedisClient)
        
        # Act
        masked = client._mask_url("redis://:password123@localhost:6379/0")
        
        # Assert
        assert "password123" not in masked
        assert "***" in masked


class TestShortMemoryOperations:
    """短期记忆操作测试"""

    @pytest.fixture
    def mock_redis_client(self):
        """创建Mock Redis客户端"""
        with patch('src.mcp_core.services.redis_client.redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            with patch('src.mcp_core.services.redis_client.ConnectionPool'):
                client = RedisClient(redis_url="redis://localhost:6379/1")
                client.client = mock_instance
                yield client

    @pytest.mark.unit
    def test_store_short_memory_success(self, mock_redis_client):
        """测试:存储短期记忆成功"""
        # Arrange
        project_id = "test-project"
        memory_data = {"memory_id": "mem_123", "content": "测试记忆"}
        relevance_score = 0.85
        
        mock_pipeline = MagicMock()
        mock_redis_client.client.pipeline.return_value.__enter__.return_value = mock_pipeline
        
        # Act
        result = mock_redis_client.store_short_memory(
            project_id, memory_data, relevance_score
        )
        
        # Assert
        assert result is True
        mock_pipeline.zadd.assert_called_once()
        mock_pipeline.expire.assert_called_once()
        mock_pipeline.zremrangebyrank.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    @pytest.mark.unit
    def test_store_short_memory_with_custom_ttl(self, mock_redis_client):
        """测试:存储短期记忆 - 自定义TTL"""
        # Arrange
        project_id = "test-project"
        memory_data = {"memory_id": "mem_123", "content": "测试记忆"}
        relevance_score = 0.85
        custom_ttl = 3600  # 1小时
        
        mock_pipeline = MagicMock()
        mock_redis_client.client.pipeline.return_value.__enter__.return_value = mock_pipeline
        
        # Act
        result = mock_redis_client.store_short_memory(
            project_id, memory_data, relevance_score, ttl=custom_ttl
        )
        
        # Assert
        assert result is True
        # 验证expire调用使用了自定义TTL
        args, kwargs = mock_pipeline.expire.call_args
        assert args[1] == custom_ttl

    @pytest.mark.unit
    def test_get_short_memories_success(self, mock_redis_client):
        """测试:检索短期记忆成功"""
        # Arrange
        project_id = "test-project"
        
        # Mock返回数据
        mock_memory1 = json.dumps({"memory_id": "mem_1", "content": "记忆1"}).encode('utf-8')
        mock_memory2 = json.dumps({"memory_id": "mem_2", "content": "记忆2"}).encode('utf-8')
        
        mock_redis_client.client.zrevrange.return_value = [
            (mock_memory1, 0.9),
            (mock_memory2, 0.8)
        ]
        
        # Act
        memories = mock_redis_client.get_short_memories(project_id, top_k=5)
        
        # Assert
        assert len(memories) == 2
        assert memories[0][0]["memory_id"] == "mem_1"
        assert memories[0][1] == 0.9
        assert memories[1][0]["memory_id"] == "mem_2"
        assert memories[1][1] == 0.8

    @pytest.mark.unit
    def test_get_short_memories_empty(self, mock_redis_client):
        """测试:检索短期记忆 - 空结果"""
        # Arrange
        project_id = "test-project"
        mock_redis_client.client.zrevrange.return_value = []
        
        # Act
        memories = mock_redis_client.get_short_memories(project_id)
        
        # Assert
        assert len(memories) == 0

    @pytest.mark.unit
    def test_get_short_memories_invalid_json(self, mock_redis_client):
        """测试:检索短期记忆 - 无效JSON"""
        # Arrange
        project_id = "test-project"
        
        # Mock返回无效JSON和有效JSON
        invalid_data = b"invalid json{{"
        valid_data = json.dumps({"memory_id": "mem_1", "content": "有效记忆"}).encode('utf-8')
        
        mock_redis_client.client.zrevrange.return_value = [
            (invalid_data, 0.9),
            (valid_data, 0.8)
        ]
        
        # Act
        memories = mock_redis_client.get_short_memories(project_id)
        
        # Assert
        assert len(memories) == 1  # 只返回有效的
        assert memories[0][0]["memory_id"] == "mem_1"

    @pytest.mark.unit
    def test_delete_short_memory_success(self, mock_redis_client):
        """测试:删除短期记忆成功"""
        # Arrange
        project_id = "test-project"
        memory_id = "mem_123"
        
        mock_memory = json.dumps({"memory_id": memory_id, "content": "要删除的记忆"}).encode('utf-8')
        mock_redis_client.client.zrange.return_value = [mock_memory]
        mock_redis_client.client.zrem.return_value = 1
        
        # Act
        result = mock_redis_client.delete_short_memory(project_id, memory_id)
        
        # Assert
        assert result is True
        mock_redis_client.client.zrem.assert_called_once()

    @pytest.mark.unit
    def test_delete_short_memory_not_found(self, mock_redis_client):
        """测试:删除短期记忆 - 不存在"""
        # Arrange
        project_id = "test-project"
        memory_id = "non_existent"
        
        mock_memory = json.dumps({"memory_id": "mem_other", "content": "其他记忆"}).encode('utf-8')
        mock_redis_client.client.zrange.return_value = [mock_memory]
        
        # Act
        result = mock_redis_client.delete_short_memory(project_id, memory_id)
        
        # Assert
        assert result is False


class TestCacheOperations:
    """缓存操作测试"""

    @pytest.fixture
    def mock_redis_client(self):
        """创建Mock Redis客户端"""
        with patch('src.mcp_core.services.redis_client.redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            with patch('src.mcp_core.services.redis_client.ConnectionPool'):
                client = RedisClient(redis_url="redis://localhost:6379/1")
                client.client = mock_instance
                yield client

    @pytest.mark.unit
    def test_cache_retrieval_result_success(self, mock_redis_client):
        """测试:缓存检索结果成功"""
        # Arrange
        project_id = "test-project"
        query = "历史时间轴"
        result = {"memories": [{"content": "测试内容"}]}
        
        mock_redis_client.client.setex.return_value = True
        
        # Act
        success = mock_redis_client.cache_retrieval_result(project_id, query, result)
        
        # Assert
        assert success is True
        mock_redis_client.client.setex.assert_called_once()
        
        # 验证cached_at字段被添加
        call_args = mock_redis_client.client.setex.call_args[0]
        cached_data = json.loads(call_args[2].decode('utf-8'))
        assert "cached_at" in cached_data

    @pytest.mark.unit
    def test_get_cached_retrieval_hit(self, mock_redis_client):
        """测试:获取缓存 - 命中"""
        # Arrange
        project_id = "test-project"
        query = "历史时间轴"
        cached_result = {"memories": [], "cached_at": 1234567890}
        
        mock_redis_client.client.get.return_value = json.dumps(cached_result).encode('utf-8')
        
        # Act
        result = mock_redis_client.get_cached_retrieval(project_id, query)
        
        # Assert
        assert result is not None
        assert result["cached_at"] == 1234567890

    @pytest.mark.unit
    def test_get_cached_retrieval_miss(self, mock_redis_client):
        """测试:获取缓存 - 未命中"""
        # Arrange
        project_id = "test-project"
        query = "不存在的查询"
        
        mock_redis_client.client.get.return_value = None
        
        # Act
        result = mock_redis_client.get_cached_retrieval(project_id, query)
        
        # Assert
        assert result is None

    @pytest.mark.unit
    def test_invalidate_cache_success(self, mock_redis_client):
        """测试:清除缓存成功"""
        # Arrange
        project_id = "test-project"
        pattern = "test*"
        
        mock_redis_client.client.keys.return_value = [b"key1", b"key2", b"key3"]
        mock_redis_client.client.delete.return_value = 3
        
        # Act
        deleted_count = mock_redis_client.invalidate_cache(project_id, pattern)
        
        # Assert
        assert deleted_count == 3
        mock_redis_client.client.delete.assert_called_once()

    @pytest.mark.unit
    def test_invalidate_cache_no_keys(self, mock_redis_client):
        """测试:清除缓存 - 无匹配键"""
        # Arrange
        project_id = "test-project"
        pattern = "non_existent*"
        
        mock_redis_client.client.keys.return_value = []
        
        # Act
        deleted_count = mock_redis_client.invalidate_cache(project_id, pattern)
        
        # Assert
        assert deleted_count == 0


class TestStatisticsOperations:
    """统计操作测试"""

    @pytest.fixture
    def mock_redis_client(self):
        """创建Mock Redis客户端"""
        with patch('src.mcp_core.services.redis_client.redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            with patch('src.mcp_core.services.redis_client.ConnectionPool'):
                client = RedisClient(redis_url="redis://localhost:6379/1")
                client.client = mock_instance
                yield client

    @pytest.mark.unit
    def test_increment_token_saved_success(self, mock_redis_client):
        """测试:累计Token成功"""
        # Arrange
        project_id = "test-project"
        tokens = 1000
        
        mock_redis_client.client.incrby.return_value = 5000
        mock_redis_client.client.expire.return_value = True
        
        # Act
        total = mock_redis_client.increment_token_saved(project_id, tokens)
        
        # Assert
        assert total == 5000
        mock_redis_client.client.incrby.assert_called_once_with(
            pytest.approx(tokens, rel=1e-9)  # 允许误差
        )

    @pytest.mark.unit
    def test_increment_token_saved_with_custom_date(self, mock_redis_client):
        """测试:累计Token - 指定日期"""
        # Arrange
        project_id = "test-project"
        tokens = 500
        custom_date = "20251120"
        
        mock_redis_client.client.incrby.return_value = 500
        mock_redis_client.client.expire.return_value = True
        
        # Act
        total = mock_redis_client.increment_token_saved(project_id, tokens, date=custom_date)
        
        # Assert
        assert total == 500
        # 验证key包含指定日期
        call_args = mock_redis_client.client.incrby.call_args[0]
        assert custom_date in call_args[0]

    @pytest.mark.unit
    def test_get_token_stats_success(self, mock_redis_client):
        """测试:获取Token统计成功"""
        # Arrange
        project_id = "test-project"
        days = 3
        
        # Mock返回不同天的统计
        mock_redis_client.client.get.side_effect = [b"1000", b"2000", b"3000"]
        
        # Act
        stats = mock_redis_client.get_token_stats(project_id, days=days)
        
        # Assert
        assert len(stats) == days
        assert all(value > 0 for value in stats.values())

    @pytest.mark.unit
    def test_get_token_stats_partial_data(self, mock_redis_client):
        """测试:获取Token统计 - 部分数据"""
        # Arrange
        project_id = "test-project"
        days = 3
        
        # Mock返回部分数据(有的天没有统计)
        mock_redis_client.client.get.side_effect = [b"1000", None, b"3000"]
        
        # Act
        stats = mock_redis_client.get_token_stats(project_id, days=days)
        
        # Assert
        assert len(stats) == days
        # 验证没有数据的天返回0
        assert 0 in stats.values()


class TestGenericOperations:
    """通用操作测试"""

    @pytest.fixture
    def mock_redis_client(self):
        """创建Mock Redis客户端"""
        with patch('src.mcp_core.services.redis_client.redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True
            
            with patch('src.mcp_core.services.redis_client.ConnectionPool'):
                client = RedisClient(redis_url="redis://localhost:6379/1")
                client.client = mock_instance
                yield client

    @pytest.mark.unit
    def test_exists_key_true(self, mock_redis_client):
        """测试:键存在"""
        # Arrange
        key = "test_key"
        mock_redis_client.client.exists.return_value = 1
        
        # Act
        result = mock_redis_client.exists(key)
        
        # Assert
        assert result is True

    @pytest.mark.unit
    def test_exists_key_false(self, mock_redis_client):
        """测试:键不存在"""
        # Arrange
        key = "non_existent_key"
        mock_redis_client.client.exists.return_value = 0
        
        # Act
        result = mock_redis_client.exists(key)
        
        # Assert
        assert result is False

    @pytest.mark.unit
    def test_delete_keys_success(self, mock_redis_client):
        """测试:删除键成功"""
        # Arrange
        keys = ("key1", "key2", "key3")
        mock_redis_client.client.delete.return_value = 3
        
        # Act
        deleted = mock_redis_client.delete(*keys)
        
        # Assert
        assert deleted == 3

    @pytest.mark.unit
    def test_delete_no_keys(self, mock_redis_client):
        """测试:删除键 - 空参数"""
        # Act
        deleted = mock_redis_client.delete()
        
        # Assert
        assert deleted == 0

    @pytest.mark.unit
    def test_ttl_key(self, mock_redis_client):
        """测试:获取TTL"""
        # Arrange
        key = "test_key"
        mock_redis_client.client.ttl.return_value = 3600
        
        # Act
        ttl = mock_redis_client.ttl(key)
        
        # Assert
        assert ttl == 3600

    @pytest.mark.unit
    def test_close_connection(self, mock_redis_client):
        """测试:关闭连接"""
        # Act
        mock_redis_client.close()
        
        # Assert
        mock_redis_client.client.close.assert_called_once()

    @pytest.mark.unit
    def test_context_manager(self, mock_redis_client):
        """测试:上下文管理器"""
        # Act
        with mock_redis_client as client:
            assert client is mock_redis_client
        
        # Assert - 退出时应该调用close
        mock_redis_client.client.close.assert_called_once()


class TestSingletonPattern:
    """单例模式测试"""

    @pytest.mark.unit
    @patch('src.mcp_core.services.redis_client.RedisClient')
    def test_get_redis_client_singleton(self, mock_redis_class):
        """测试:单例模式"""
        # Arrange
        mock_instance = MagicMock()
        mock_redis_class.return_value = mock_instance
        
        # 重置单例
        import src.mcp_core.services.redis_client as redis_module
        redis_module._redis_client_instance = None
        
        # Act
        client1 = get_redis_client()
        client2 = get_redis_client()
        
        # Assert
        assert client1 is client2  # 应该是同一个实例
        assert mock_redis_class.call_count == 1  # 只初始化一次
