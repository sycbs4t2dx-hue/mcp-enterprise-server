"""
Token优化核心服务
实现内容压缩、Token计算、压缩率统计
"""

import hashlib
import time
from typing import Any, Dict, Optional

from ..common.config import get_settings
from ..common.logger import get_context_logger
from .compressors.code_compressor import CodeCompressor
from .compressors.text_compressor import TextCompressor
from .redis_client import get_redis_client

logger = get_context_logger(__name__)


class TokenOptimizationService:
    """Token优化服务"""

    def __init__(self):
        """初始化Token优化服务"""
        self.settings = get_settings()
        self.code_compressor = CodeCompressor()
        self.text_compressor = TextCompressor()
        self.redis_client = get_redis_client()

        logger.info("Token优化服务初始化完成")

    def compress_content(
        self,
        content: str,
        content_type: Optional[str] = None,
        compression_ratio: Optional[float] = None,
        enable_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        压缩内容

        Args:
            content: 原始内容
            content_type: 内容类型(code/text/auto),auto会自动检测
            compression_ratio: 压缩比例(0-1),为None时使用配置
            enable_cache: 是否启用缓存

        Returns:
            {
                original_tokens: int,
                compressed_tokens: int,
                compression_rate: float,
                compressed_content: str,
                content_type_detected: str,
                cache_hit: bool
            }
        """
        start_time = time.time()

        # 检查缓存
        if enable_cache:
            cached = self._get_cached_compression(content)
            if cached:
                cached["cache_hit"] = True
                logger.debug("命中压缩缓存", extra={"content_hash": self._hash_content(content)[:8]})
                return cached

        # 参数默认值
        if compression_ratio is None:
            compression_ratio = self.settings.token_optimization.compression_ratio

        # 内容长度检查
        min_length = self.settings.token_optimization.compression_min_length
        if len(content) < min_length:
            logger.debug(f"内容过短({len(content)}),跳过压缩")
            original_tokens = self._count_tokens(content)
            return {
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_rate": 0.0,
                "compressed_content": content,
                "content_type_detected": "short",
                "cache_hit": False,
            }

        # 自动检测内容类型
        if content_type is None or content_type == "auto":
            content_type = self._detect_content_type(content)

        # 选择压缩器
        if content_type == "code":
            compressed = self.code_compressor.compress(content, compression_ratio)
        else:
            compressed = self.text_compressor.compress(content, compression_ratio)

        # 计算Token
        original_tokens = self._count_tokens(content)
        compressed_tokens = self._count_tokens(compressed)

        # 计算压缩率
        compression_rate = (
            (original_tokens - compressed_tokens) / original_tokens
            if original_tokens > 0
            else 0.0
        )

        result = {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_rate": compression_rate,
            "compressed_content": compressed,
            "content_type_detected": content_type,
            "cache_hit": False,
        }

        # 缓存结果
        if enable_cache:
            self._cache_compression(content, result)

        elapsed = time.time() - start_time
        logger.info(
            f"内容压缩完成",
            extra={
                "type": content_type,
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "rate": f"{compression_rate:.2%}",
                "elapsed": f"{elapsed:.3f}s",
            },
        )

        return result

    def batch_compress(
        self,
        contents: list,
        content_types: Optional[list] = None,
        compression_ratio: Optional[float] = None,
    ) -> list:
        """
        批量压缩内容

        Args:
            contents: 内容列表
            content_types: 内容类型列表,长度需与contents一致
            compression_ratio: 压缩比例

        Returns:
            压缩结果列表
        """
        if content_types is None:
            content_types = [None] * len(contents)

        if len(content_types) != len(contents):
            raise ValueError("content_types长度必须与contents一致")

        results = []
        for content, content_type in zip(contents, content_types):
            result = self.compress_content(
                content, content_type, compression_ratio
            )
            results.append(result)

        total_saved = sum(
            r["original_tokens"] - r["compressed_tokens"] for r in results
        )

        logger.info(
            f"批量压缩完成",
            extra={
                "count": len(contents),
                "total_tokens_saved": total_saved,
            },
        )

        return results

    def calculate_token_savings(
        self, original_content: str, compressed_content: str
    ) -> Dict[str, Any]:
        """
        计算Token节省量

        Args:
            original_content: 原始内容
            compressed_content: 压缩后内容

        Returns:
            {original_tokens, compressed_tokens, tokens_saved, saving_rate}
        """
        original_tokens = self._count_tokens(original_content)
        compressed_tokens = self._count_tokens(compressed_content)
        tokens_saved = original_tokens - compressed_tokens
        saving_rate = (
            tokens_saved / original_tokens if original_tokens > 0 else 0.0
        )

        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "tokens_saved": tokens_saved,
            "saving_rate": saving_rate,
        }

    # ==================== 辅助方法 ====================

    def _count_tokens(self, text: str) -> int:
        """
        估算Token数量

        使用简化算法: 1 token ≈ 4字符(英文) 或 1.5字符(中文)

        Args:
            text: 文本内容

        Returns:
            Token数量(估算)
        """
        # 分离中英文
        import re

        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        english_chars = len(text) - chinese_chars

        # 中文: 1.5字符/token, 英文: 4字符/token
        tokens = int(chinese_chars / 1.5 + english_chars / 4)

        return max(tokens, 1)  # 至少1个token

    def _detect_content_type(self, content: str) -> str:
        """
        自动检测内容类型

        Args:
            content: 内容

        Returns:
            内容类型(code/text)
        """
        # 代码特征检测
        code_indicators = [
            "def ",
            "class ",
            "function ",
            "import ",
            "const ",
            "var ",
            "let ",
            "public ",
            "private ",
            "=>",
            "{",
            "}",
            "[]",
            "()",
        ]

        # 计算代码特征数量
        code_score = sum(
            1 for indicator in code_indicators if indicator in content
        )

        # 如果包含3个以上代码特征,判定为代码
        if code_score >= 3 or content.count("\n") / max(len(content), 1) > 0.05:
            return "code"

        return "text"

    def _hash_content(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _get_cached_compression(
        self, content: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的压缩结果"""
        content_hash = self._hash_content(content)
        cache_key = f"compress:{content_hash}"

        try:
            cached = self.redis_client.client.get(cache_key)
            if cached:
                import json

                return json.loads(cached.decode("utf-8"))
            return None
        except Exception as e:
            logger.warning(f"获取压缩缓存失败: {e}")
            return None

    def _cache_compression(
        self, content: str, result: Dict[str, Any]
    ) -> bool:
        """缓存压缩结果"""
        content_hash = self._hash_content(content)
        cache_key = f"compress:{content_hash}"

        try:
            import json

            ttl = self.settings.token_optimization.cache_ttl
            self.redis_client.client.setex(
                cache_key, ttl, json.dumps(result, ensure_ascii=False).encode("utf-8")
            )
            return True
        except Exception as e:
            logger.warning(f"缓存压缩结果失败: {e}")
            return False

    def get_compression_stats(self, project_id: str, days: int = 7) -> Dict[str, Any]:
        """
        获取压缩统计

        Args:
            project_id: 项目ID
            days: 统计天数

        Returns:
            压缩统计信息
        """
        token_stats = self.redis_client.get_token_stats(project_id, days)

        total_saved = sum(token_stats.values())
        avg_saved_per_day = total_saved / days if days > 0 else 0

        return {
            "project_id": project_id,
            "days": days,
            "total_tokens_saved": total_saved,
            "avg_tokens_saved_per_day": int(avg_saved_per_day),
            "daily_stats": token_stats,
        }


# 单例模式
_token_service_instance: Optional[TokenOptimizationService] = None


def get_token_service() -> TokenOptimizationService:
    """
    获取Token服务单例

    Returns:
        TokenOptimizationService实例
    """
    global _token_service_instance

    if _token_service_instance is None:
        _token_service_instance = TokenOptimizationService()

    return _token_service_instance
