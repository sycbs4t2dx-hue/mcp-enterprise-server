"""
文本压缩器
使用TextRank算法提取文本摘要
"""

import re
from typing import List, Optional

from ...common.logger import get_logger

logger = get_logger(__name__)


class TextCompressor:
    """文本压缩器"""

    def __init__(self):
        """初始化文本压缩器"""
        pass

    def compress(self, text: str, compression_ratio: float = 0.2) -> str:
        """
        压缩文本

        策略:
        1. 优先使用TextRank算法提取摘要
        2. 降级策略:句子评分+Top-K选择
        3. 兜底策略:简单截断

        Args:
            text: 原始文本
            compression_ratio: 压缩比例(保留比例)

        Returns:
            压缩后的文本
        """
        try:
            # 尝试TextRank算法
            compressed = self._compress_with_textrank(text, compression_ratio)
            if compressed:
                return compressed

        except Exception as e:
            logger.debug(f"TextRank压缩失败: {e}")

        # 降级策略:基于句子重要性
        try:
            compressed = self._compress_with_sentence_ranking(text, compression_ratio)
            if compressed:
                return compressed
        except Exception as e:
            logger.debug(f"句子排序压缩失败: {e}")

        # 兜底策略:智能截断
        return self._compress_with_truncation(text, compression_ratio)

    # ==================== TextRank算法 ====================

    def _compress_with_textrank(self, text: str, ratio: float) -> Optional[str]:
        """
        使用TextRank算法压缩

        注意: 需要安装summa库
        """
        try:
            from summa.summarizer import summarize

            # TextRank摘要
            summary = summarize(text, ratio=ratio, split=False)

            if summary and len(summary) > 50:
                return summary

            return None

        except ImportError:
            logger.debug("summa库未安装,跳过TextRank")
            return None
        except Exception as e:
            logger.debug(f"TextRank执行失败: {e}")
            return None

    # ==================== 句子排序压缩 ====================

    def _compress_with_sentence_ranking(self, text: str, ratio: float) -> str:
        """
        基于句子重要性的压缩

        策略:
        1. 分句
        2. 计算每句的重要性得分
        3. 选择Top-K句子
        4. 按原顺序重排
        """
        # 分句
        sentences = self._split_sentences(text)

        if len(sentences) <= 3:
            # 句子太少,直接返回
            return text

        # 计算目标句子数
        target_count = max(int(len(sentences) * ratio), 2)

        # 计算每句得分
        scored_sentences = []
        for idx, sent in enumerate(sentences):
            score = self._calculate_sentence_score(sent, idx, len(sentences))
            scored_sentences.append((idx, sent, score))

        # 排序并选择Top-K
        scored_sentences.sort(key=lambda x: x[2], reverse=True)
        selected = scored_sentences[:target_count]

        # 按原顺序重排
        selected.sort(key=lambda x: x[0])

        # 合并句子
        compressed = " ".join(sent for _, sent, _ in selected)

        return compressed

    def _split_sentences(self, text: str) -> List[str]:
        """
        分句

        支持中英文
        """
        # 简化的分句规则
        # 句子分隔符: 。！？.!?\n
        pattern = r"[。！？.!?\n]+"

        sentences = re.split(pattern, text)

        # 过滤空句
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _calculate_sentence_score(
        self, sentence: str, position: int, total: int
    ) -> float:
        """
        计算句子重要性得分

        考虑因素:
        1. 位置(开头和结尾句子更重要)
        2. 长度(过短或过长的句子权重降低)
        3. 关键词密度
        """
        score = 0.0

        # 1. 位置得分(首尾句子更重要)
        if position == 0:
            score += 0.4  # 第一句
        elif position == total - 1:
            score += 0.3  # 最后一句
        elif position < 3:
            score += 0.2  # 前三句

        # 2. 长度得分(20-100字最佳)
        length = len(sentence)
        if 20 <= length <= 100:
            score += 0.3
        elif 10 <= length < 20 or 100 < length <= 150:
            score += 0.1

        # 3. 关键词得分
        keywords = ["核心", "重要", "关键", "主要", "必须", "需要", "问题", "方案", "结论"]
        for keyword in keywords:
            if keyword in sentence:
                score += 0.05

        # 4. 数字和列表得分(包含具体信息)
        if re.search(r"\d+", sentence) or re.search(r"[①②③④⑤]|[1-9]\.", sentence):
            score += 0.1

        return score

    # ==================== 智能截断 ====================

    def _compress_with_truncation(self, text: str, ratio: float) -> str:
        """
        智能截断压缩

        策略:
        1. 保留前N%的内容
        2. 在句子边界截断
        3. 添加省略号
        """
        target_length = int(len(text) * ratio)

        # 在目标长度附近查找句子边界
        search_start = max(target_length - 50, 0)
        search_end = min(target_length + 50, len(text))
        search_text = text[search_start:search_end]

        # 查找句子结束符
        sentence_ends = [
            search_start + match.start()
            for match in re.finditer(r"[。！？.!?\n]", search_text)
        ]

        if sentence_ends:
            # 在最接近目标长度的句子边界截断
            cut_position = min(sentence_ends, key=lambda x: abs(x - target_length))
            compressed = text[: cut_position + 1]
        else:
            # 无句子边界,直接截断
            compressed = text[:target_length]

        # 添加省略号
        if len(compressed) < len(text):
            compressed += " ..."

        return compressed.strip()

    # ==================== 辅助方法 ====================

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取关键词

        简化实现:基于词频
        """
        # 分词(简化)
        words = re.findall(r"\b\w{2,}\b", text.lower())

        # 停用词
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "的",
            "了",
            "在",
            "是",
            "有",
            "和",
            "这",
            "个",
        }

        # 过滤停用词
        words = [w for w in words if w not in stop_words and len(w) > 1]

        # 统计词频
        from collections import Counter

        word_counts = Counter(words)

        # 返回Top-K
        return [word for word, _ in word_counts.most_common(top_k)]

    def get_compression_info(self) -> dict:
        """获取压缩器信息"""
        return {
            "compressor": "TextCompressor",
            "algorithms": [
                "TextRank (primary)",
                "Sentence ranking (fallback)",
                "Smart truncation (fallback)",
            ],
            "supported_languages": ["zh-CN", "en", "mixed"],
        }
