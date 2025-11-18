"""
嵌入服务单元测试
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.mcp_core.services.embedding_service import EmbeddingService


@pytest.fixture
def embedding_service():
    """Embedding Service fixture"""
    with patch("src.mcp_core.services.embedding_service.SentenceTransformer") as mock_model:
        # Mock模型
        mock_instance = Mock()
        mock_instance.get_sentence_embedding_dimension.return_value = 384
        mock_instance.max_seq_length = 512
        mock_instance.encode.return_value = np.random.rand(384)
        mock_model.return_value = mock_instance

        service = EmbeddingService()
        service.model = mock_instance
        return service


class TestEmbeddingService:
    """嵌入服务测试类"""

    def test_encode_single(self, embedding_service):
        """测试单条文本嵌入生成"""
        text = "这是一段测试文本"
        embedding = embedding_service.encode_single(text)

        assert embedding is not None
        assert len(embedding) == 384  # 默认维度

    def test_encode_single_returns_list(self, embedding_service):
        """测试返回列表格式"""
        text = "测试"
        embedding = embedding_service.encode_single(text, convert_to_numpy=False)

        assert isinstance(embedding, (list, np.ndarray))

    def test_encode_batch(self, embedding_service):
        """测试批量嵌入生成"""
        texts = ["文本1", "文本2", "文本3"]

        # Mock批量返回
        embedding_service.model.encode.return_value = np.random.rand(3, 384)

        embeddings = embedding_service.encode_batch(texts, batch_size=2)

        assert embeddings.shape == (3, 384)
        embedding_service.model.encode.assert_called_once()

    def test_calculate_similarity_cosine(self, embedding_service):
        """测试余弦相似度计算"""
        emb1 = np.random.rand(384)
        emb2 = emb1.copy()  # 相同向量

        similarity = embedding_service.calculate_similarity(
            emb1, emb2, metric="cosine"
        )

        assert 0.99 <= similarity <= 1.0  # 相同向量相似度应接近1

    def test_calculate_similarity_different_vectors(self, embedding_service):
        """测试不同向量的相似度"""
        emb1 = np.random.rand(384)
        emb2 = np.random.rand(384)

        similarity = embedding_service.calculate_similarity(
            emb1, emb2, metric="cosine"
        )

        assert 0.0 <= similarity <= 1.0

    def test_find_most_similar(self, embedding_service):
        """测试查找最相似向量"""
        query = np.random.rand(384)
        candidates = np.random.rand(10, 384)

        # 将第3个候选设为与query完全相同
        candidates[2] = query.copy()

        results = embedding_service.find_most_similar(
            query, candidates, top_k=5, metric="cosine"
        )

        assert len(results) == 5
        assert results[0][0] == 2  # 第3个应该是最相似的
        assert results[0][1] >= 0.99  # 相似度接近1

    def test_get_dimension(self, embedding_service):
        """测试获取嵌入维度"""
        dim = embedding_service.get_dimension()
        assert dim == 384

    def test_get_model_info(self, embedding_service):
        """测试获取模型信息"""
        info = embedding_service.get_model_info()

        assert "model_name" in info
        assert "dimension" in info
        assert "device" in info
        assert info["dimension"] == 384

    def test_cache_functionality(self, embedding_service):
        """测试LRU缓存"""
        text = "缓存测试文本"

        # 第一次调用
        result1 = embedding_service.encode_cached(text)

        # 第二次调用(应该从缓存返回)
        result2 = embedding_service.encode_cached(text)

        # 结果应相同
        assert result1 == result2

        # 清除缓存
        embedding_service.clear_cache()

    def test_invalid_similarity_metric(self, embedding_service):
        """测试无效的相似度度量"""
        emb1 = np.random.rand(384)
        emb2 = np.random.rand(384)

        with pytest.raises(ValueError, match="不支持的相似度度量"):
            embedding_service.calculate_similarity(
                emb1, emb2, metric="invalid_metric"
            )


# 性能测试
class TestEmbeddingPerformance:
    """嵌入服务性能测试"""

    def test_batch_encoding_performance(self, embedding_service):
        """测试批量编码性能"""
        import time

        texts = ["测试文本"] * 100

        # Mock返回
        embedding_service.model.encode.return_value = np.random.rand(100, 384)

        start = time.time()
        embeddings = embedding_service.encode_batch(texts, batch_size=32)
        elapsed = time.time() - start

        assert embeddings.shape == (100, 384)
        # Mock环境下应该很快
        assert elapsed < 1.0, f"批量编码耗时{elapsed:.3f}s"
