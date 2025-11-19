"""
Memory Service Unit Tests
测试记忆服务的核心功能
"""
import pytest
from src.mcp_core.services.memory_service import MemoryService


class TestMemoryService:
    """记忆服务测试类"""

    @pytest.mark.unit
    def test_extract_keywords_chinese(self, memory_service):
        """测试中文关键词提取"""
        text = "历史时间轴项目使用React和D3.js开发"
        keywords = memory_service._extract_keywords(text, max_keywords=10)

        # 验证关键词提取成功
        assert len(keywords) > 0
        assert "历史" in keywords
        assert "时间轴" in keywords
        assert "项目" in keywords
        assert "react" in keywords or "React" in keywords
        assert "d3" in keywords or "D3" in keywords

    @pytest.mark.unit
    def test_extract_keywords_english(self, memory_service):
        """测试英文关键词提取"""
        text = "The MCP server provides 37 tools for project management"
        keywords = memory_service._extract_keywords(text, max_keywords=10)

        assert len(keywords) > 0
        assert "mcp" in keywords
        assert "server" in keywords
        assert "tools" in keywords
        assert "project" in keywords
        assert "management" in keywords

    @pytest.mark.unit
    def test_extract_keywords_mixed(self, memory_service):
        """测试中英文混合关键词提取"""
        text = "MCP Enterprise Server支持中文分词using jieba library"
        keywords = memory_service._extract_keywords(text, max_keywords=10)

        assert len(keywords) > 0
        # 中文
        assert "支持" in keywords or "中文" in keywords or "分词" in keywords
        # 英文
        assert "mcp" in keywords or "enterprise" in keywords or "server" in keywords

    @pytest.mark.unit
    @pytest.mark.db
    def test_store_memory_success(self, memory_service, sample_memory_data):
        """测试存储记忆成功场景"""
        result = memory_service.store_memory(
            project_id=sample_memory_data["project_id"],
            content=sample_memory_data["content"],
            memory_level=sample_memory_data["memory_level"],
            category=sample_memory_data.get("category"),
            confidence=sample_memory_data.get("confidence")
        )

        assert result["success"] is True
        assert "memory_id" in result
        assert result["memory_level"] == "long_term"

    @pytest.mark.unit
    @pytest.mark.db
    def test_retrieve_memory_success(self, memory_service, sample_memory_data):
        """测试检索记忆成功场景"""
        # 先存储记忆
        memory_service.store_memory(
            project_id=sample_memory_data["project_id"],
            content=sample_memory_data["content"],
            memory_level="long_term"
        )

        # 检索记忆
        result = memory_service.retrieve_memory(
            project_id=sample_memory_data["project_id"],
            query="历史时间轴",
            top_k=5
        )

        assert isinstance(result, dict)
        assert "memories" in result
        assert "count" in result
        assert result["count"] > 0
        assert len(result["memories"]) > 0

        # 验证返回的记忆包含相关内容
        first_memory = result["memories"][0]
        assert "content" in first_memory
        assert "relevance_score" in first_memory
        assert first_memory["relevance_score"] > 0

    @pytest.mark.unit
    def test_retrieve_memory_empty_query(self, memory_service, sample_project_id):
        """测试空查询"""
        with pytest.raises(ValueError, match="query不能为空"):
            memory_service.retrieve_memory(
                project_id=sample_project_id,
                query="",
                top_k=5
            )

    @pytest.mark.unit
    def test_retrieve_memory_invalid_project_id(self, memory_service):
        """测试无效项目ID"""
        with pytest.raises(ValueError, match="project_id不能为空"):
            memory_service.retrieve_memory(
                project_id="",
                query="test",
                top_k=5
            )

    @pytest.mark.unit
    @pytest.mark.db
    def test_retrieve_memory_no_results(self, memory_service):
        """测试检索不到结果的情况"""
        result = memory_service.retrieve_memory(
            project_id="non-existent-project",
            query="不存在的关键词xyzabc123",
            top_k=5
        )

        assert isinstance(result, dict)
        assert result["count"] == 0
        assert len(result["memories"]) == 0

    @pytest.mark.unit
    @pytest.mark.db
    def test_store_multiple_memories(self, memory_service, sample_project_id):
        """测试存储多条记忆"""
        memories = [
            "MCP服务器提供37个工具",
            "使用jieba进行中文分词",
            "集成Redis缓存服务",
            "支持MySQL数据库",
            "向量检索使用Milvus"
        ]

        stored_ids = []
        for content in memories:
            result = memory_service.store_memory(
                project_id=sample_project_id,
                content=content,
                memory_level="long_term"
            )
            assert result["success"] is True
            stored_ids.append(result["memory_id"])

        # 验证所有记忆都已存储
        assert len(stored_ids) == len(memories)
        assert len(set(stored_ids)) == len(stored_ids)  # 所有ID唯一

    @pytest.mark.unit
    @pytest.mark.db
    def test_relevance_score_ordering(self, memory_service, sample_project_id):
        """测试相关性得分排序"""
        # 存储多条记忆
        memory_service.store_memory(
            project_id=sample_project_id,
            content="历史时间轴项目使用React和D3.js开发",
            memory_level="long_term",
            confidence=0.9
        )
        memory_service.store_memory(
            project_id=sample_project_id,
            content="历史时间轴的数据存储在MongoDB",
            memory_level="long_term",
            confidence=0.8
        )
        memory_service.store_memory(
            project_id=sample_project_id,
            content="完全不相关的内容about something else",
            memory_level="long_term",
            confidence=0.7
        )

        # 检索
        result = memory_service.retrieve_memory(
            project_id=sample_project_id,
            query="历史时间轴",
            top_k=3
        )

        # 验证结果按相关性排序
        assert len(result["memories"]) > 0
        scores = [m["relevance_score"] for m in result["memories"]]
        assert scores == sorted(scores, reverse=True)  # 降序排列

        # 验证最相关的记忆排在前面
        top_memory = result["memories"][0]
        assert "历史时间轴" in top_memory["content"]


# Integration tests
class TestMemoryServiceIntegration:
    """记忆服务集成测试"""

    @pytest.mark.integration
    @pytest.mark.db
    @pytest.mark.redis
    @pytest.mark.slow
    def test_full_memory_workflow(self, memory_service, sample_project_id):
        """测试完整的记忆工作流"""
        # 1. 存储长期记忆
        long_term_result = memory_service.store_memory(
            project_id=sample_project_id,
            content="MCP企业级服务器v2.0.0已发布",
            memory_level="long_term",
            category="release",
            confidence=0.95
        )
        assert long_term_result["success"] is True

        # 2. 存储短期记忆
        short_term_result = memory_service.store_memory(
            project_id=sample_project_id,
            content="当前正在测试记忆功能",
            memory_level="short_term"
        )
        assert short_term_result["success"] is True

        # 3. 检索记忆
        retrieve_result = memory_service.retrieve_memory(
            project_id=sample_project_id,
            query="MCP服务器",
            top_k=5
        )

        # 4. 验证检索结果
        assert retrieve_result["count"] > 0
        assert len(retrieve_result["memories"]) > 0

        # 5. 验证包含长期记忆
        has_long_term = any(
            "MCP" in m["content"] and "v2.0.0" in m["content"]
            for m in retrieve_result["memories"]
        )
        assert has_long_term is True
