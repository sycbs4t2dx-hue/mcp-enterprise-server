"""
嵌入向量生成服务
使用sentence-transformers生成文本嵌入
支持从本地路径加载模型，避免重复下载
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from ..common.config import get_settings
from ..common.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """嵌入向量生成服务"""

    def __init__(self, model_name: Optional[str] = None):
        """
        初始化嵌入服务

        Args:
            model_name: 模型名称,为None时使用配置文件
        """
        settings = get_settings()

        # 优先使用本地模型路径
        self.model_path = self._resolve_model_path(model_name)

        # 检测设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(
            f"加载嵌入模型",
            extra={"model": self.model_path, "device": self.device},
        )

        try:
            # 设置环境变量
            self._setup_environment(settings)

            # 加载模型 (支持本地路径或HF仓库名称)
            self.model = SentenceTransformer(self.model_path, device=self.device)

            # 获取嵌入维度
            self.dimension = self.model.get_sentence_embedding_dimension()

            logger.info(
                f"嵌入模型加载成功",
                extra={"model": self.model_path, "dimension": self.dimension},
            )

        except Exception as e:
            logger.error(f"嵌入模型加载失败: {e}")
            raise

    def _resolve_model_path(self, model_name: Optional[str] = None) -> str:
        """
        解析模型路径 (优先使用本地路径)

        Args:
            model_name: 模型名称

        Returns:
            模型路径 (本地路径或HF仓库名称)
        """
        settings = get_settings()

        # 获取模型配置
        local_path_str = None
        model_repo = None

        if hasattr(settings, 'models') and settings.models:
            models_config = settings.models
            embedding_config = getattr(models_config, 'embedding', None)

            if embedding_config:
                # embedding_config 可能是dict类型
                if isinstance(embedding_config, dict):
                    local_path_str = embedding_config.get('local_path')
                    model_repo = embedding_config.get('model_name')
                else:
                    local_path_str = embedding_config.local_path
                    model_repo = embedding_config.model_name

                # 1. 优先使用本地路径 (如果存在且有效)
                if models_config.prefer_local and local_path_str:
                    local_path = Path(local_path_str)

                    # 检查路径是否存在且包含必要文件
                    if local_path.exists() and self._validate_model_directory(local_path):
                        logger.info(
                            f"✅ 使用本地模型",
                            extra={"path": str(local_path)}
                        )
                        return str(local_path)
                    else:
                        logger.warning(
                            f"⚠️ 本地模型路径无效或不完整: {local_path}",
                            extra={"reason": "目录不存在或缺少必要文件"}
                        )

            # 2. 使用HF仓库名称 (会自动下载)
            repo_name = model_name or model_repo
            logger.info(
                f"📥 将从Hugging Face加载模型",
                extra={"repo": repo_name}
            )
            return repo_name
        else:
            # 兼容旧配置
            return model_name or settings.token_optimization.text_model

    def _validate_model_directory(self, model_dir: Path) -> bool:
        """
        验证模型目录是否包含必要文件

        Args:
            model_dir: 模型目录

        Returns:
            是否有效
        """
        # 必须存在的文件 (至少包含其中之一)
        required_files = [
            "config.json",
            "pytorch_model.bin",
            "model.safetensors",
        ]

        for file_name in required_files:
            if (model_dir / file_name).exists():
                return True

        return False

    def _setup_environment(self, settings):
        """
        设置Hugging Face环境变量

        Args:
            settings: 配置对象
        """
        if hasattr(settings, 'models') and settings.models:
            models_config = settings.models
            hf_config = models_config.huggingface

            # 离线模式
            if hf_config.offline_mode:
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                os.environ["HF_HUB_OFFLINE"] = "1"
                logger.info("🔌 Hugging Face离线模式已启用")

            # 使用镜像站
            if hf_config.use_mirror and hf_config.mirror_url:
                os.environ["HF_ENDPOINT"] = hf_config.mirror_url
                logger.info(
                    f"🌍 使用Hugging Face镜像",
                    extra={"mirror": hf_config.mirror_url}
                )

            # 设置缓存目录 (统一存储位置)
            cache_dir = Path(models_config.local_model_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)
            os.environ["HF_HOME"] = str(cache_dir)

    def encode_single(
        self,
        text: str,
        normalize: bool = True,
        convert_to_numpy: bool = True,
    ) -> Union[np.ndarray, List[float]]:
        """
        生成单条文本嵌入

        Args:
            text: 输入文本
            normalize: 是否归一化(用于余弦相似度)
            convert_to_numpy: 是否转为numpy数组

        Returns:
            嵌入向量
        """
        try:
            embedding = self.model.encode(
                text,
                normalize_embeddings=normalize,
                convert_to_numpy=convert_to_numpy,
                show_progress_bar=False,
            )

            logger.debug(
                f"生成嵌入",
                extra={"text_length": len(text), "dimension": len(embedding)},
            )

            return embedding if convert_to_numpy else embedding.tolist()

        except Exception as e:
            logger.error(f"生成嵌入失败: {e}", extra={"text": text[:100]})
            # 返回零向量作为降级
            return np.zeros(self.dimension) if convert_to_numpy else [0.0] * self.dimension

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        批量生成嵌入(性能优化)

        Args:
            texts: 文本列表
            batch_size: 批处理大小
            normalize: 是否归一化
            show_progress: 是否显示进度条

        Returns:
            嵌入矩阵 (num_texts, dimension)
        """
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
                show_progress_bar=show_progress,
            )

            logger.info(
                f"批量生成嵌入",
                extra={
                    "count": len(texts),
                    "batch_size": batch_size,
                    "shape": embeddings.shape,
                },
            )

            return embeddings

        except Exception as e:
            logger.error(f"批量生成嵌入失败: {e}", extra={"count": len(texts)})
            return np.zeros((len(texts), self.dimension))

    @lru_cache(maxsize=1000)
    def encode_cached(self, text: str) -> tuple:
        """
        带LRU缓存的嵌入生成(适用于常用短文本)

        Args:
            text: 输入文本

        Returns:
            嵌入向量(tuple格式,支持hash)

        Note:
            - 缓存最多1000条
            - 适用于常用关键词、标签等短文本
            - 长文本不建议缓存
        """
        embedding = self.encode_single(text, convert_to_numpy=True)
        return tuple(embedding.tolist())

    def calculate_similarity(
        self,
        embedding1: Union[np.ndarray, List[float]],
        embedding2: Union[np.ndarray, List[float]],
        metric: str = "cosine",
    ) -> float:
        """
        计算两个嵌入的相似度

        Args:
            embedding1: 嵌入1
            embedding2: 嵌入2
            metric: 相似度度量(cosine/euclidean/dot)

        Returns:
            相似度分数
        """
        # 转为numpy数组
        emb1 = np.array(embedding1) if not isinstance(embedding1, np.ndarray) else embedding1
        emb2 = np.array(embedding2) if not isinstance(embedding2, np.ndarray) else embedding2

        if metric == "cosine":
            # 余弦相似度
            from sklearn.metrics.pairwise import cosine_similarity

            sim = cosine_similarity(emb1.reshape(1, -1), emb2.reshape(1, -1))[0][0]

        elif metric == "euclidean":
            # 欧氏距离(转为相似度:1 / (1 + distance))
            from sklearn.metrics.pairwise import euclidean_distances

            dist = euclidean_distances(emb1.reshape(1, -1), emb2.reshape(1, -1))[0][0]
            sim = 1.0 / (1.0 + dist)

        elif metric == "dot":
            # 点积
            sim = np.dot(emb1, emb2)

        else:
            raise ValueError(f"不支持的相似度度量: {metric}")

        return float(sim)

    def calculate_similarity_matrix(
        self,
        embeddings1: np.ndarray,
        embeddings2: Optional[np.ndarray] = None,
        metric: str = "cosine",
    ) -> np.ndarray:
        """
        计算嵌入矩阵的相似度矩阵

        Args:
            embeddings1: 嵌入矩阵1 (m, dimension)
            embeddings2: 嵌入矩阵2 (n, dimension),为None时与embeddings1自身计算
            metric: 相似度度量

        Returns:
            相似度矩阵 (m, n)
        """
        if embeddings2 is None:
            embeddings2 = embeddings1

        if metric == "cosine":
            from sklearn.metrics.pairwise import cosine_similarity

            sim_matrix = cosine_similarity(embeddings1, embeddings2)

        elif metric == "euclidean":
            from sklearn.metrics.pairwise import euclidean_distances

            dist_matrix = euclidean_distances(embeddings1, embeddings2)
            sim_matrix = 1.0 / (1.0 + dist_matrix)

        elif metric == "dot":
            sim_matrix = np.dot(embeddings1, embeddings2.T)

        else:
            raise ValueError(f"不支持的相似度度量: {metric}")

        return sim_matrix

    def find_most_similar(
        self,
        query_embedding: Union[np.ndarray, List[float]],
        candidate_embeddings: np.ndarray,
        top_k: int = 5,
        metric: str = "cosine",
    ) -> List[tuple]:
        """
        查找最相似的候选

        Args:
            query_embedding: 查询嵌入
            candidate_embeddings: 候选嵌入矩阵 (num_candidates, dimension)
            top_k: 返回Top-K
            metric: 相似度度量

        Returns:
            [(index, similarity_score), ...]
        """
        # 转为numpy数组
        query = (
            np.array(query_embedding)
            if not isinstance(query_embedding, np.ndarray)
            else query_embedding
        )

        # 计算相似度
        similarities = []
        for idx, candidate in enumerate(candidate_embeddings):
            sim = self.calculate_similarity(query, candidate, metric=metric)
            similarities.append((idx, sim))

        # 排序并返回Top-K
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_dimension(self) -> int:
        """获取嵌入维度"""
        return self.dimension

    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "max_seq_length": self.model.max_seq_length,
        }

    def clear_cache(self) -> None:
        """清除LRU缓存"""
        self.encode_cached.cache_clear()
        logger.info("嵌入缓存已清除")


# 单例模式
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取嵌入服务单例

    Returns:
        EmbeddingService实例
    """
    global _embedding_service_instance

    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()

    return _embedding_service_instance
