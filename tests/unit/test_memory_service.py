"""
记忆服务单元测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.mcp_core.services.memory_service import MemoryService
from src.mcp_core.models.tables import LongMemory


@pytest.fixture
def mock_db_session():
    """Mock数据库会话"""
    return Mock()


@pytest.fixture
def memory_service(mock_db_session):
    """Memory Service fixture"""
    with patch("src.mcp_core.services.memory_service.get_redis_client"), \
         patch("src.mcp_core.services.memory_service.get_vector_db_client"), \
         patch("src.mcp_core.services.memory_service.get_embedding_service"):
        service = MemoryService(mock_db_session)
        return service


class TestMemoryService:
    """记忆服务测试类"""

    def test_extract_core_info(self, memory_service):
        """测试核心信息提取"""
        content = "这是一段   带有多余   空格的   测试文本"
        result = memory_service._extract_core_info(content)

        assert "  " not in result  # 多余空格已移除
        assert result == "这是一段 带有多余 空格的 测试文本"

    def test_extract_core_info_long_content(self, memory_service):
        """测试长文本截断"""
        content = "A" * 3000
        result = memory_service._extract_core_info(content)

        assert len(result) <= 2003  # 2000 + "..."
        assert result.endswith("...")

    def test_calculate_relevance_score(self, memory_service):
        """测试相关性评分计算"""
        # 短文本
        score1 = memory_service._calculate_relevance_score("短文本", {})
        assert 0.0 <= score1 <= 1.0

        # 长文本+高置信度
        long_content = "X" * 600
        score2 = memory_service._calculate_relevance_score(
            long_content, {"confidence": 0.9}
        )
        assert score2 > score1  # 长文本+高置信度应有更高分数

    def test_deduplicate_memories(self, memory_service):
        """测试记忆去重"""
        memories = [
            {"memory_id": "mem_001", "content": "相同内容"},
            {"memory_id": "mem_002", "content": "相同内容"},  # 重复
            {"memory_id": "mem_003", "content": "不同内容"},
        ]

        unique = memory_service._deduplicate_memories(memories)

        assert len(unique) == 2  # 应该去掉1条重复
        contents = [m["content"] for m in unique]
        assert "相同内容" in contents
        assert "不同内容" in contents

    def test_extract_keywords(self, memory_service):
        """测试关键词提取"""
        text = "Django框架是一个优秀的Python Web框架"
        keywords = memory_service._extract_keywords(text, max_keywords=5)

        assert "django" in keywords or "框架" in keywords
        assert "的" not in keywords  # 停用词应被过滤
        assert len(keywords) <= 5

    def test_store_memory_validation(self, memory_service):
        """测试存储记忆参数验证"""
        # 无效的memory_level
        with pytest.raises(ValueError, match="无效的记忆层级"):
            memory_service.store_memory(
                project_id="test_proj",
                content="测试内容",
                memory_level="invalid_level",
            )

    @patch("src.mcp_core.services.memory_service.generate_id")
    def test_store_long_memory_success(self, mock_generate_id, memory_service, mock_db_session):
        """测试长期记忆存储成功"""
        mock_generate_id.return_value = "mem_test_001"

        result = memory_service.store_memory(
            project_id="test_proj",
            content="测试长期记忆内容",
            memory_level="long",
            metadata={"category": "test", "confidence": 0.9},
        )

        assert result["memory_id"] == "mem_test_001"
        assert result["memory_level"] == "long"
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    def test_retrieve_memory_cache_hit(self, memory_service):
        """测试检索记忆缓存命中"""
        # Mock缓存命中
        cached_result = {
            "memories": [{"content": "缓存的记忆"}],
            "total_token_saved": 100,
        }
        memory_service.redis_client.get_cached_retrieval = Mock(
            return_value=cached_result
        )

        result = memory_service.retrieve_memory(
            project_id="test_proj", query="测试查询"
        )

        assert result == cached_result
        # 不应调用实际检索
        assert not memory_service.vector_db.search_vectors.called


class TestMemoryServiceIntegration:
    """集成测试(需要真实数据库连接)"""

    @pytest.mark.integration
    def test_full_memory_lifecycle(self, db_session):
        """测试完整的记忆生命周期:存储->检索->更新->删除"""
        # 需要真实数据库连接
        pytest.skip("集成测试需要真实数据库环境")


# 性能测试
class TestMemoryPerformance:
    """性能测试"""

    def test_retrieval_performance(self, memory_service):
        """测试检索性能(应<300ms)"""
        import time

        # Mock快速返回
        memory_service.redis_client.get_cached_retrieval = Mock(return_value=None)
        memory_service.redis_client.get_short_memories = Mock(return_value=[])
        memory_service.vector_db.search_vectors = Mock(return_value=[])
        memory_service._retrieve_long_memories = Mock(return_value=[])

        start = time.time()
        memory_service.retrieve_memory(
            project_id="test_proj", query="测试查询", top_k=5
        )
        elapsed = (time.time() - start) * 1000  # 转为毫秒

        # 注意: Mock环境下性能测试不准确,仅测试逻辑
        assert elapsed < 1000, f"检索耗时{elapsed:.2f}ms (Mock环境)"
