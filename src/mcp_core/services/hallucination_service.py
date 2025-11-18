"""
幻觉抑制服务
通过语义相似度检测和自适应阈值算法识别模型幻觉
"""

import re
import time
from typing import Any, Dict, List, Optional

import numpy as np

from ..common.config import get_settings
from ..common.logger import get_context_logger
from .embedding_service import get_embedding_service
from .memory_service import MemoryService

logger = get_context_logger(__name__)


class HallucinationValidationService:
    """幻觉验证服务"""

    def __init__(self, memory_service: Optional[MemoryService] = None):
        """
        初始化幻觉验证服务

        Args:
            memory_service: 记忆服务实例,用于检索相关记忆
        """
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
        self.memory_service = memory_service
        self.base_threshold = self.settings.anti_hallucination.base_threshold

        logger.info("幻觉抑制服务初始化完成")

    def detect_hallucination(
        self,
        project_id: str,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        检测输出是否为幻觉

        Args:
            project_id: 项目ID
            output: 待检测的输出内容
            context: 上下文信息(用于自适应阈值)
            threshold: 相似度阈值,为None时使用配置

        Returns:
            {
                is_hallucination: bool,
                confidence: float,
                matched_memories: List[str],
                threshold_used: float,
                reason: str,
                details: Dict
            }
        """
        start_time = time.time()

        # 使用自适应阈值
        if threshold is None:
            threshold = self._calculate_adaptive_threshold(output, context or {})
        else:
            threshold = max(
                self.settings.anti_hallucination.adaptive_min_threshold,
                min(threshold, self.settings.anti_hallucination.adaptive_max_threshold),
            )

        # 生成输出嵌入
        output_embedding = self.embedding_service.encode_single(output)

        # 检索相关记忆
        if self.memory_service:
            memories = self._retrieve_relevant_memories(project_id, output)
        else:
            logger.warning("未提供memory_service,无法检索记忆")
            return self._build_no_memory_result(threshold)

        # 如果没有相关记忆,判定为幻觉
        if not memories or len(memories) == 0:
            elapsed = time.time() - start_time
            logger.warning(
                "未找到相关记忆",
                extra={
                    "project_id": project_id,
                    "output_preview": output[:50],
                },
            )
            return {
                "is_hallucination": True,
                "confidence": 0.0,
                "matched_memories": [],
                "threshold_used": threshold,
                "reason": "无相关记忆支撑",
                "details": {"elapsed": f"{elapsed:.3f}s"},
            }

        # 计算与记忆的相似度
        similarities = []
        matched_ids = []

        for mem in memories[:5]:  # 只检查Top5
            mem_embedding = self.embedding_service.encode_single(mem["content"])
            similarity = self.embedding_service.calculate_similarity(
                output_embedding, mem_embedding, metric="cosine"
            )
            similarities.append(similarity)
            matched_ids.append(mem["memory_id"])

        # 计算平均相似度和最高相似度
        avg_similarity = float(np.mean(similarities))
        max_similarity = float(np.max(similarities))

        # 使用最高相似度作为置信度
        confidence = max_similarity

        # 判断是否为幻觉
        is_hallucination = confidence < threshold

        elapsed = time.time() - start_time

        result = {
            "is_hallucination": is_hallucination,
            "confidence": confidence,
            "matched_memories": matched_ids,
            "threshold_used": threshold,
            "reason": self._get_hallucination_reason(
                is_hallucination, confidence, threshold
            ),
            "details": {
                "avg_similarity": avg_similarity,
                "max_similarity": max_similarity,
                "memories_checked": len(similarities),
                "elapsed": f"{elapsed:.3f}s",
            },
        }

        logger.info(
            f"幻觉检测完成",
            extra={
                "project_id": project_id,
                "is_hallucination": is_hallucination,
                "confidence": f"{confidence:.3f}",
                "threshold": f"{threshold:.3f}",
                "elapsed": f"{elapsed:.3f}s",
            },
        )

        return result

    def batch_detect(
        self,
        project_id: str,
        outputs: List[str],
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量检测幻觉

        Args:
            project_id: 项目ID
            outputs: 输出列表
            threshold: 相似度阈值

        Returns:
            检测结果列表
        """
        results = []

        for output in outputs:
            result = self.detect_hallucination(project_id, output, threshold=threshold)
            results.append(result)

        hallucination_count = sum(1 for r in results if r["is_hallucination"])
        hallucination_rate = hallucination_count / len(results) if results else 0

        logger.info(
            f"批量幻觉检测完成",
            extra={
                "total": len(outputs),
                "hallucinations": hallucination_count,
                "rate": f"{hallucination_rate:.2%}",
            },
        )

        return results

    # ==================== 自适应阈值算法 ====================

    def _calculate_adaptive_threshold(
        self, output: str, context: Dict[str, Any]
    ) -> float:
        """
        计算自适应阈值

        考虑因素:
        1. 查询长度(长查询降低阈值)
        2. 代码块数量(代码相关降低阈值)
        3. 技术术语密度(术语多降低阈值)
        4. 记忆数量(记忆少提高阈值)
        5. 用户历史幻觉率(幻觉率高提高阈值)

        Args:
            output: 输出内容
            context: 上下文信息

        Returns:
            调整后的阈值
        """
        adjustments = []
        base = self.base_threshold

        # 1. 查询长度调整
        if len(output) > 200:
            adjustments.append(("长查询", -0.05))

        # 2. 代码块检测
        code_blocks = output.count("```") // 2
        if code_blocks > 2:
            adjustments.append(("代码块多", -0.08))
        elif code_blocks > 0:
            adjustments.append(("包含代码", -0.03))

        # 3. 技术术语密度
        tech_terms = [
            "API",
            "SDK",
            "数据库",
            "框架",
            "接口",
            "配置",
            "部署",
            "架构",
            "服务",
            "模块",
        ]
        term_count = sum(1 for term in tech_terms if term in output)
        if term_count >= 3:
            adjustments.append(("技术术语密集", -0.05))

        # 4. 记忆数量(从上下文获取)
        memory_count = context.get("memory_count", 100)
        if memory_count < 10:
            adjustments.append(("记忆少", +0.05))

        # 5. 用户历史幻觉率(从上下文获取)
        user_hallucination_rate = context.get("user_hallucination_rate", 0.0)
        if user_hallucination_rate > 0.10:
            adjustments.append(("用户幻觉率高", +0.10))

        # 6. 复杂任务检测
        if self._is_complex_task(output):
            adjustments.append(("复杂任务", -0.05))

        # 应用调整
        total_adjustment = sum(adj for _, adj in adjustments)
        adjusted_threshold = base + total_adjustment

        # 限制范围
        adjusted_threshold = max(
            self.settings.anti_hallucination.adaptive_min_threshold,
            min(
                adjusted_threshold,
                self.settings.anti_hallucination.adaptive_max_threshold,
            ),
        )

        # 记录调整详情
        if adjustments:
            logger.debug(
                f"阈值自适应调整",
                extra={
                    "base": f"{base:.3f}",
                    "adjustments": adjustments,
                    "final": f"{adjusted_threshold:.3f}",
                },
            )

        return adjusted_threshold

    def _is_complex_task(self, output: str) -> bool:
        """
        判断是否为复杂任务

        复杂任务特征:
        - 输出长度>500字符
        - 包含2个以上代码块
        - 包含列表/步骤
        """
        return (
            len(output) > 500
            or output.count("```") > 4
            or len(re.findall(r"[1-9]\.|①②③", output)) > 3
        )

    # ==================== 辅助方法 ====================

    def _retrieve_relevant_memories(
        self, project_id: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        try:
            result = self.memory_service.retrieve_memory(
                project_id=project_id,
                query=query,
                top_k=top_k,
                memory_levels=["mid", "long"],  # 只检索中长期记忆
            )
            return result.get("memories", [])

        except Exception as e:
            logger.error(f"检索记忆失败: {e}", extra={"project_id": project_id})
            return []

    def _build_no_memory_result(self, threshold: float) -> Dict[str, Any]:
        """构建无记忆服务时的结果"""
        return {
            "is_hallucination": False,  # 无法判断,保守策略
            "confidence": 0.5,
            "matched_memories": [],
            "threshold_used": threshold,
            "reason": "无记忆服务,无法验证",
            "details": {},
        }

    def _get_hallucination_reason(
        self, is_hallucination: bool, confidence: float, threshold: float
    ) -> str:
        """生成幻觉判定原因"""
        if is_hallucination:
            return f"相似度{confidence:.3f}低于阈值{threshold:.3f},可能为幻觉"
        else:
            return f"相似度{confidence:.3f}高于阈值{threshold:.3f},验证通过"

    def get_hallucination_stats(
        self, project_id: str, time_range: str = "7d"
    ) -> Dict[str, Any]:
        """
        获取幻觉统计

        Args:
            project_id: 项目ID
            time_range: 时间范围(1d/7d/30d)

        Returns:
            幻觉统计信息
        """
        # 简化实现:从Redis统计
        # 实际应从审计日志或专门的统计表查询
        return {
            "project_id": project_id,
            "time_range": time_range,
            "total_detections": 0,
            "hallucination_count": 0,
            "hallucination_rate": 0.0,
            "avg_confidence": 0.0,
            "note": "统计功能待完善(需要审计日志支持)",
        }


# 工厂函数
def create_hallucination_service(
    memory_service: MemoryService,
) -> HallucinationValidationService:
    """
    创建幻觉验证服务

    Args:
        memory_service: 记忆服务实例

    Returns:
        HallucinationValidationService实例
    """
    return HallucinationValidationService(memory_service)
