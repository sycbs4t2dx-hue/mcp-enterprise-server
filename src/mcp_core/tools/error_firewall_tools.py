"""
错误防火墙MCP工具
提供错误模式记录、相似错误查找、解决方案推荐
"""

from typing import Any, Dict, Optional

from ..services.error_firewall import ErrorPattern, get_error_firewall
from ..common.logger import get_logger

logger = get_logger(__name__)


def record_error_pattern(
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    solution: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """
    记录错误模式到防火墙系统

    Args:
        error_type: 错误类型（如 ValueError, ConnectionError）
        error_message: 错误消息
        stack_trace: 堆栈跟踪（可选）
        context: 上下文信息（可选）
        solution: 解决方案（可选）
        tags: 标签，逗号分隔（可选）

    Returns:
        记录结果
    """
    try:
        firewall = get_error_firewall()

        # 解析标签
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        # 创建错误模式
        pattern = ErrorPattern(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context,
            solution=solution,
            tags=tag_list,
        )

        # 记录到向量数据库
        success, error_id = firewall.record_error(pattern)

        if success:
            return {
                "success": True,
                "error_id": error_id,
                "message": "错误模式已记录",
            }
        else:
            return {
                "success": False,
                "message": "记录失败",
            }

    except Exception as e:
        logger.error(f"记录错误模式失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def find_similar_errors(
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    查找相似的历史错误

    Args:
        error_type: 错误类型
        error_message: 错误消息
        stack_trace: 堆栈跟踪（可选）
        top_k: 返回结果数量

    Returns:
        相似错误列表
    """
    try:
        firewall = get_error_firewall()

        # 创建查询模式
        pattern = ErrorPattern(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
        )

        # 查找相似错误
        similar_errors = firewall.find_similar_errors(pattern, top_k)

        return {
            "success": True,
            "similar_errors": similar_errors,
            "count": len(similar_errors),
        }

    except Exception as e:
        logger.error(f"查找相似错误失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "similar_errors": [],
        }


def get_error_solution(
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取错误的推荐解决方案

    Args:
        error_type: 错误类型
        error_message: 错误消息
        stack_trace: 堆栈跟踪（可选）

    Returns:
        解决方案
    """
    try:
        firewall = get_error_firewall()

        # 创建错误模式
        pattern = ErrorPattern(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
        )

        # 获取解决方案
        solution = firewall.get_solution(pattern)

        # 同时查找相似错误
        similar_errors = firewall.find_similar_errors(pattern, top_k=3)

        return {
            "success": True,
            "solution": solution,
            "similar_errors": similar_errors,
            "confidence": similar_errors[0]["similarity"] if similar_errors else 0,
        }

    except Exception as e:
        logger.error(f"获取错误解决方案失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "solution": None,
        }


def update_error_solution(
    error_id: str,
    solution: str,
    success: bool = True,
) -> Dict[str, Any]:
    """
    更新错误的解决方案（学习）

    Args:
        error_id: 错误ID
        solution: 解决方案
        success: 解决是否成功

    Returns:
        更新结果
    """
    try:
        firewall = get_error_firewall()

        # 学习解决方案
        updated = firewall.learn_from_resolution(error_id, solution, success)

        if updated:
            return {
                "success": True,
                "message": "解决方案已更新",
                "error_id": error_id,
            }
        else:
            return {
                "success": False,
                "message": "更新失败",
            }

    except Exception as e:
        logger.error(f"更新解决方案失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_error_firewall_stats() -> Dict[str, Any]:
    """
    获取错误防火墙统计信息

    Returns:
        统计信息
    """
    try:
        firewall = get_error_firewall()
        stats = firewall.get_error_stats()

        return {
            "success": True,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"获取错误防火墙统计失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "stats": {},
        }