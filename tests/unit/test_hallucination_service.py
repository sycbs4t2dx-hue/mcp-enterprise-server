"""
幻觉抑制服务单元测试
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.mcp_core.services.hallucination_service import (
    HallucinationValidationService,
    create_hallucination_service,
)


@pytest.fixture
def mock_memory_service():
    """Mock记忆服务"""
    service = Mock()
    service.retrieve_memory = Mock(
        return_value={
            "memories": [
                {"memory_id": "mem_001", "content": "项目使用Django框架", "relevance_score": 0.9},
                {"memory_id": "mem_002", "content": "数据库是PostgreSQL", "relevance_score": 0.85},
            ]
        }
    )
    return service


@pytest.fixture
def hallucination_service(mock_memory_service):
    """幻觉服务fixture"""
    with patch("src.mcp_core.services.hallucination_service.get_embedding_service") as mock_embed:
        # Mock嵌入服务
        mock_embed_instance = Mock()
        mock_embed_instance.encode_single = Mock(return_value=np.random.rand(384))
        mock_embed_instance.calculate_similarity = Mock(return_value=0.85)
        mock_embed.return_value = mock_embed_instance

        service = HallucinationValidationService(mock_memory_service)
        return service


class TestHallucinationValidationService:
    """幻觉验证服务测试"""

    def test_init(self, hallucination_service):
        """测试初始化"""
        assert hallucination_service.base_threshold == 0.65
        assert hallucination_service.memory_service is not None

    def test_detect_no_hallucination(self, hallucination_service):
        """测试正常输出(无幻觉)"""
        # Mock高相似度
        hallucination_service.embedding_service.calculate_similarity = Mock(return_value=0.90)

        result = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="项目使用Django框架进行开发"
        )

        assert result["is_hallucination"] == False
        assert result["confidence"] >= 0.65
        assert len(result["matched_memories"]) > 0

    def test_detect_hallucination(self, hallucination_service):
        """测试幻觉输出"""
        # Mock低相似度
        hallucination_service.embedding_service.calculate_similarity = Mock(return_value=0.30)

        result = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="项目使用非常罕见的框架XYZ"
        )

        assert result["is_hallucination"] == True
        assert result["confidence"] < 0.65
        assert "低于阈值" in result["reason"]

    def test_detect_no_memories(self, hallucination_service):
        """测试无相关记忆情况"""
        # Mock空记忆
        hallucination_service.memory_service.retrieve_memory = Mock(
            return_value={"memories": []}
        )

        result = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="测试内容"
        )

        assert result["is_hallucination"] == True
        assert result["confidence"] == 0.0
        assert "无相关记忆" in result["reason"]

    def test_detect_without_memory_service(self):
        """测试无记忆服务情况"""
        with patch("src.mcp_core.services.hallucination_service.get_embedding_service"):
            service = HallucinationValidationService(memory_service=None)

            result = service.detect_hallucination(
                project_id="test_proj",
                output="测试内容"
            )

            assert result["is_hallucination"] == False  # 保守策略
            assert "无记忆服务" in result["reason"]

    def test_batch_detect(self, hallucination_service):
        """测试批量检测"""
        outputs = [
            "正常输出1",
            "正常输出2",
            "可能的幻觉输出",
        ]

        # Mock混合结果
        call_count = [0]

        def mock_similarity(*args, **kwargs):
            call_count[0] += 1
            return 0.90 if call_count[0] <= 2 else 0.30

        hallucination_service.embedding_service.calculate_similarity = mock_similarity

        results = hallucination_service.batch_detect("test_proj", outputs)

        assert len(results) == 3
        assert not results[0]["is_hallucination"]
        assert not results[1]["is_hallucination"]
        assert results[2]["is_hallucination"]


class TestAdaptiveThreshold:
    """自适应阈值测试"""

    def test_long_query_adjustment(self, hallucination_service):
        """测试长查询阈值调整"""
        long_output = "测试内容" * 100  # 长查询
        short_output = "测试内容"

        threshold_long = hallucination_service._calculate_adaptive_threshold(
            long_output, {}
        )
        threshold_short = hallucination_service._calculate_adaptive_threshold(
            short_output, {}
        )

        # 长查询阈值应更低
        assert threshold_long < threshold_short or threshold_long <= 0.65

    def test_code_block_adjustment(self, hallucination_service):
        """测试代码块阈值调整"""
        code_output = "```python\ncode\n```\n" * 3
        text_output = "普通文本内容"

        threshold_code = hallucination_service._calculate_adaptive_threshold(
            code_output, {}
        )
        threshold_text = hallucination_service._calculate_adaptive_threshold(
            text_output, {}
        )

        # 包含代码块应降低阈值
        assert threshold_code <= threshold_text

    def test_tech_terms_adjustment(self, hallucination_service):
        """测试技术术语阈值调整"""
        tech_output = "API接口调用数据库框架配置部署架构服务"
        normal_output = "普通的文本内容"

        threshold_tech = hallucination_service._calculate_adaptive_threshold(
            tech_output, {}
        )
        threshold_normal = hallucination_service._calculate_adaptive_threshold(
            normal_output, {}
        )

        # 技术术语多应降低阈值
        assert threshold_tech <= threshold_normal

    def test_memory_count_adjustment(self, hallucination_service):
        """测试记忆数量阈值调整"""
        # 记忆少
        threshold_few = hallucination_service._calculate_adaptive_threshold(
            "测试", {"memory_count": 5}
        )

        # 记忆多
        threshold_many = hallucination_service._calculate_adaptive_threshold(
            "测试", {"memory_count": 100}
        )

        # 记忆少应提高阈值(更严格)
        assert threshold_few >= threshold_many

    def test_threshold_bounds(self, hallucination_service):
        """测试阈值边界"""
        # 极端调整
        threshold = hallucination_service._calculate_adaptive_threshold(
            "```code```" * 100,  # 大量代码
            {"memory_count": 1, "user_hallucination_rate": 0.5}
        )

        # 应在配置范围内
        assert 0.40 <= threshold <= 0.85

    def test_is_complex_task(self, hallucination_service):
        """测试复杂任务识别"""
        # 长输出
        assert hallucination_service._is_complex_task("A" * 600) == True

        # 多代码块
        assert hallucination_service._is_complex_task("```\ncode\n```" * 3) == True

        # 多列表项
        assert hallucination_service._is_complex_task("1. 项\n2. 项\n3. 项\n4. 项") == True

        # 简单输出
        assert hallucination_service._is_complex_task("简短文本") == False


class TestFactoryFunction:
    """工厂函数测试"""

    def test_create_hallucination_service(self, mock_memory_service):
        """测试工厂函数"""
        with patch("src.mcp_core.services.hallucination_service.get_embedding_service"):
            service = create_hallucination_service(mock_memory_service)

            assert isinstance(service, HallucinationValidationService)
            assert service.memory_service == mock_memory_service


class TestEdgeCases:
    """边缘案例测试"""

    def test_empty_output(self, hallucination_service):
        """测试空输出"""
        result = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output=""
        )

        assert "is_hallucination" in result

    def test_very_short_output(self, hallucination_service):
        """测试极短输出"""
        result = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="是"
        )

        assert "is_hallucination" in result

    def test_custom_threshold(self, hallucination_service):
        """测试自定义阈值"""
        # Mock相似度
        hallucination_service.embedding_service.calculate_similarity = Mock(return_value=0.70)

        # 使用较低阈值(0.60)
        result_low = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="测试",
            threshold=0.60
        )

        # 使用较高阈值(0.80)
        result_high = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="测试",
            threshold=0.80
        )

        # 相似度0.70: 低阈值通过,高阈值不通过
        assert result_low["is_hallucination"] == False
        assert result_high["is_hallucination"] == True

    def test_threshold_clamping(self, hallucination_service):
        """测试阈值钳位"""
        # 极低阈值
        result_low = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="测试",
            threshold=0.10
        )

        # 极高阈值
        result_high = hallucination_service.detect_hallucination(
            project_id="test_proj",
            output="测试",
            threshold=0.99
        )

        # 应被钳位到配置范围
        assert 0.40 <= result_low["threshold_used"] <= 0.85
        assert 0.40 <= result_high["threshold_used"] <= 0.85
