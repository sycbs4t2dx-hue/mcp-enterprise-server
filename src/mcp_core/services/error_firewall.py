"""
错误防火墙服务
提供错误模式学习、相似错误检测、自动解决方案推荐
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..common.logger import get_logger
from .embedding_service import get_embedding_service
from .vector_db import get_vector_db_client

logger = get_logger(__name__)


class ErrorPattern:
    """错误模式定义"""

    def __init__(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        solution: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        self.error_type = error_type
        self.error_message = error_message
        self.stack_trace = stack_trace or ""
        self.context = context or {}
        self.solution = solution
        self.tags = tags or []
        self.timestamp = datetime.now()

    def to_text(self) -> str:
        """转换为文本表示（用于向量化）"""
        parts = [
            f"Error Type: {self.error_type}",
            f"Message: {self.error_message}",
        ]
        if self.stack_trace:
            parts.append(f"Stack Trace: {self.stack_trace[:500]}")
        if self.context:
            parts.append(f"Context: {json.dumps(self.context, default=str)[:200]}")
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")
        return "\n".join(parts)

    def get_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.error_type}:{self.error_message}:{self.stack_trace}"
        return hashlib.md5(content.encode()).hexdigest()


class ErrorFirewall:
    """错误防火墙主类"""

    def __init__(self):
        """初始化错误防火墙"""
        self.vector_db = get_vector_db_client()
        self.embedding_service = get_embedding_service()
        self.collection_name = "error_vectors"
        self.similarity_threshold = 0.85  # 相似度阈值

        # 错误解决方案缓存
        self.solution_cache: Dict[str, str] = {}

        # 预定义的错误解决方案
        self.predefined_solutions = {
            "ConnectionError": "检查网络连接和服务端点配置",
            "TimeoutError": "增加超时时间或优化查询性能",
            "IntegrityError": "检查数据完整性约束，可能存在重复键或外键冲突",
            "ImportError": "检查依赖包是否已安装，运行 pip install -r requirements.txt",
            "KeyError": "检查字典键是否存在，使用 .get() 方法提供默认值",
            "AttributeError": "检查对象是否有该属性，可能是拼写错误或API变更",
            "ValueError": "检查输入值的类型和范围是否正确",
            "TypeError": "检查参数类型是否匹配函数签名",
            "MemoryError": "优化内存使用，考虑批处理或增加系统内存",
            "PermissionError": "检查文件/目录权限，可能需要管理员权限",
        }

        logger.info("错误防火墙初始化完成")

    def record_error(self, error_pattern: ErrorPattern) -> Tuple[bool, str]:
        """
        记录错误模式到向量数据库

        Args:
            error_pattern: 错误模式对象

        Returns:
            (是否成功, 错误ID)
        """
        try:
            # 生成错误ID
            error_id = error_pattern.get_id()

            # 检查是否已存在
            existing = self.vector_db.query_vectors(
                self.collection_name,
                expr=f'error_id == "{error_id}"',
                output_fields=["error_id"],
                limit=1,
            )

            if existing:
                logger.debug(f"错误模式已存在: {error_id}")
                return True, error_id

            # 生成向量
            text = error_pattern.to_text()
            embedding = self.embedding_service.generate_embedding(text)

            # 准备数据
            data = [
                {
                    "error_id": error_id,
                    "embedding": embedding,
                    "error_scene": json.dumps({
                        "type": error_pattern.error_type,
                        "message": error_pattern.error_message,
                        "solution": error_pattern.solution,
                        "tags": error_pattern.tags,
                    }, ensure_ascii=False)[:100],
                    "error_type": error_pattern.error_type,
                    "created_at": int(error_pattern.timestamp.timestamp()),
                }
            ]

            # 插入向量数据库
            success, count = self.vector_db.insert_vectors(
                self.collection_name, data
            )

            if success:
                logger.info(
                    f"错误模式记录成功",
                    extra={
                        "error_id": error_id,
                        "error_type": error_pattern.error_type,
                    },
                )
                # 缓存解决方案
                if error_pattern.solution:
                    self.solution_cache[error_id] = error_pattern.solution

            return success, error_id

        except Exception as e:
            logger.error(f"记录错误模式失败: {e}")
            return False, ""

    def find_similar_errors(
        self, error_pattern: ErrorPattern, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        查找相似的错误模式

        Args:
            error_pattern: 要查询的错误模式
            top_k: 返回结果数量

        Returns:
            相似错误列表
        """
        try:
            # 生成查询向量
            text = error_pattern.to_text()
            query_embedding = self.embedding_service.generate_embedding(text)

            # 向量检索
            results = self.vector_db.search_vectors(
                self.collection_name,
                query_vectors=[query_embedding],
                top_k=top_k,
                output_fields=["error_id", "error_scene", "error_type", "created_at"],
                query_text=f"Error: {error_pattern.error_type}",
            )

            if not results or not results[0]:
                return []

            # 格式化结果
            similar_errors = []
            for hit in results[0]:
                if hit["score"] >= self.similarity_threshold:
                    try:
                        error_scene = json.loads(hit["entity"].get("error_scene", "{}"))
                    except Exception:
                        error_scene = {}

                    similar_errors.append({
                        "error_id": hit["entity"]["error_id"],
                        "error_type": hit["entity"]["error_type"],
                        "similarity": round(hit["score"], 3),
                        "error_scene": error_scene,
                        "solution": error_scene.get("solution") or
                                   self.solution_cache.get(hit["entity"]["error_id"]),
                        "created_at": datetime.fromtimestamp(
                            hit["entity"].get("created_at", 0)
                        ).isoformat(),
                    })

            return similar_errors

        except Exception as e:
            logger.error(f"查找相似错误失败: {e}")
            return []

    def get_solution(self, error_pattern: ErrorPattern) -> Optional[str]:
        """
        获取错误解决方案

        Args:
            error_pattern: 错误模式

        Returns:
            解决方案文本或None
        """
        # 1. 先查找相似错误
        similar_errors = self.find_similar_errors(error_pattern, top_k=3)

        if similar_errors:
            # 返回最相似错误的解决方案
            for error in similar_errors:
                if error.get("solution"):
                    logger.info(
                        f"找到相似错误解决方案",
                        extra={
                            "error_type": error_pattern.error_type,
                            "similarity": error["similarity"],
                        },
                    )
                    return error["solution"]

        # 2. 使用预定义解决方案
        if error_pattern.error_type in self.predefined_solutions:
            return self.predefined_solutions[error_pattern.error_type]

        # 3. 生成通用建议
        general_advice = self._generate_general_advice(error_pattern)
        return general_advice

    def _generate_general_advice(self, error_pattern: ErrorPattern) -> str:
        """生成通用错误建议"""
        advice_parts = [
            f"遇到 {error_pattern.error_type} 错误",
            "建议采取以下步骤：",
            "1. 检查错误消息和堆栈跟踪",
            "2. 验证输入数据和参数",
            "3. 查看相关日志文件",
        ]

        # 根据错误类型添加特定建议
        if "Connection" in error_pattern.error_type:
            advice_parts.append("4. 检查网络连接和服务状态")
        elif "Permission" in error_pattern.error_type:
            advice_parts.append("4. 检查文件/目录权限设置")
        elif "Memory" in error_pattern.error_type:
            advice_parts.append("4. 监控内存使用情况")
        else:
            advice_parts.append("4. 搜索错误消息获取更多信息")

        return "\n".join(advice_parts)

    def learn_from_resolution(
        self, error_id: str, solution: str, success: bool = True
    ) -> bool:
        """
        从错误解决中学习

        Args:
            error_id: 错误ID
            solution: 解决方案
            success: 解决是否成功

        Returns:
            是否更新成功
        """
        try:
            if success:
                # 缓存成功的解决方案
                self.solution_cache[error_id] = solution
                logger.info(
                    f"学习到新的解决方案",
                    extra={"error_id": error_id, "solution_length": len(solution)},
                )
            return True
        except Exception as e:
            logger.error(f"学习解决方案失败: {e}")
            return False

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            stats = self.vector_db.get_collection_stats(self.collection_name)

            # 统计错误类型分布
            error_types = {}
            recent_errors = self.vector_db.query_vectors(
                self.collection_name,
                expr="error_id != ''",
                output_fields=["error_type"],
                limit=1000,
            )

            for error in recent_errors:
                error_type = error.get("error_type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

            return {
                "total_error_patterns": stats.get("num_entities", 0),
                "error_type_distribution": error_types,
                "solution_cache_size": len(self.solution_cache),
                "is_loaded": stats.get("is_loaded", False),
            }
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {
                "total_error_patterns": 0,
                "error_type_distribution": {},
                "solution_cache_size": 0,
                "is_loaded": False,
            }


# 单例模式
_error_firewall_instance: Optional[ErrorFirewall] = None


def get_error_firewall() -> ErrorFirewall:
    """获取错误防火墙单例"""
    global _error_firewall_instance

    if _error_firewall_instance is None:
        _error_firewall_instance = ErrorFirewall()

    return _error_firewall_instance