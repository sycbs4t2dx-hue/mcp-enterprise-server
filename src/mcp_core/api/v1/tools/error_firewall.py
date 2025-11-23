"""
错误防火墙MCP工具
提供错误记录、检查、查询等功能
"""

from typing import Any, Dict, List, Optional

from src.mcp_core.services.error_firewall_service import get_error_firewall_service
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)


async def error_firewall_record(
    error_type: str,
    error_scene: str,
    error_pattern: Dict[str, Any],
    error_message: str,
    solution: Optional[str] = None,
    solution_confidence: float = 0.0,
    block_level: str = "warning",
    auto_fix: bool = False,
    db_session=None
) -> Dict[str, Any]:
    """
    记录错误到错误防火墙知识库

    Args:
        error_type: 错误类型 (如: ios_build, npm_install, api_call等)
        error_scene: 错误场景的简短描述
        error_pattern: 错误特征模式 (JSON对象)
        error_message: 完整错误信息
        solution: 推荐的解决方案
        solution_confidence: 解决方案置信度 (0-1)
        block_level: 拦截级别 (none/warning/block)
        auto_fix: 是否支持自动修复
        db_session: 数据库会话

    Returns:
        记录结果

    示例:
        await error_firewall_record(
            error_type="ios_build",
            error_scene="iOS编译时选择不存在的虚拟设备",
            error_pattern={
                "device_name": "iPhone 15",
                "os_version": "17.0",
                "operation": "build"
            },
            error_message="Error: Unable to boot device in current state: Shutdown",
            solution="请使用以下可用设备: iPhone 15 Pro (17.2), iPhone 14 (16.4)",
            solution_confidence=0.95,
            block_level="block"
        )
    """
    try:
        if not db_session:
            return {
                "success": False,
                "error": "数据库会话未提供"
            }

        firewall = get_error_firewall_service(db_session)

        result = firewall.record_error(
            error_type=error_type,
            error_scene=error_scene,
            error_pattern=error_pattern,
            error_message=error_message,
            solution=solution,
            solution_confidence=solution_confidence,
            block_level=block_level,
            auto_fix=auto_fix
        )

        logger.info(
            f"错误已记录",
            extra={
                "error_type": error_type,
                "error_id": result.get("error_id"),
                "is_new": result.get("is_new")
            }
        )

        return result

    except Exception as e:
        logger.error(f"记录错误失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def error_firewall_check(
    operation_type: str,
    operation_params: Dict[str, Any],
    session_id: Optional[str] = None,
    db_session=None
) -> Dict[str, Any]:
    """
    检查操作是否应该被拦截

    在执行可能导致错误的操作前调用此工具进行检查

    Args:
        operation_type: 操作类型
        operation_params: 操作参数 (JSON对象)
        session_id: 会话ID (可选)
        db_session: 数据库会话

    Returns:
        检查结果，包含是否拦截、风险等级、匹配的错误、建议方案等

    示例:
        result = await error_firewall_check(
            operation_type="ios_build",
            operation_params={
                "device_name": "iPhone 15",
                "os_version": "17.0"
            }
        )

        if result["should_block"]:
            print(f"⚠️ 操作被拦截: {result['message']}")
            print(f"建议方案: {result['solution']}")
        elif result["should_warn"]:
            print(f"⚠️ 警告: {result['message']}")
    """
    try:
        if not db_session:
            return {
                "success": False,
                "should_block": False,
                "risk_level": "unknown",
                "error": "数据库会话未提供"
            }

        firewall = get_error_firewall_service(db_session)

        result = firewall.check_operation(
            operation_type=operation_type,
            operation_params=operation_params,
            session_id=session_id
        )

        # 记录检查结果
        if result.get("should_block"):
            logger.warning(
                f"操作被拦截",
                extra={
                    "operation_type": operation_type,
                    "error_id": result.get("matched_error", {}).get("error_id"),
                    "risk_level": result.get("risk_level")
                }
            )
        elif result.get("should_warn"):
            logger.info(
                f"操作警告",
                extra={
                    "operation_type": operation_type,
                    "risk_level": result.get("risk_level")
                }
            )

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error(f"检查操作失败: {e}")
        return {
            "success": False,
            "should_block": False,
            "risk_level": "unknown",
            "error": str(e)
        }


async def error_firewall_query(
    error_id: Optional[str] = None,
    error_type: Optional[str] = None,
    limit: int = 20,
    db_session=None
) -> Dict[str, Any]:
    """
    查询错误防火墙中的错误记录

    Args:
        error_id: 错误ID (精确查询)
        error_type: 错误类型 (模糊查询)
        limit: 返回数量限制
        db_session: 数据库会话

    Returns:
        错误记录列表

    示例:
        # 查询特定错误
        result = await error_firewall_query(error_id="abc123...")

        # 查询特定类型的最近错误
        result = await error_firewall_query(
            error_type="ios_build",
            limit=10
        )

        # 查询所有最近错误
        result = await error_firewall_query(limit=50)
    """
    try:
        if not db_session:
            return {
                "success": False,
                "errors": [],
                "error": "数据库会话未提供"
            }

        firewall = get_error_firewall_service(db_session)

        # 精确查询
        if error_id:
            error = firewall.get_error_by_id(error_id)
            return {
                "success": True,
                "errors": [error] if error else [],
                "count": 1 if error else 0
            }

        # 查询最近错误
        errors = firewall.get_recent_errors(limit=limit)

        # 如果指定了error_type，过滤结果
        if error_type:
            errors = [e for e in errors if e["error_type"] == error_type]

        return {
            "success": True,
            "errors": errors,
            "count": len(errors)
        }

    except Exception as e:
        logger.error(f"查询错误失败: {e}")
        return {
            "success": False,
            "errors": [],
            "error": str(e)
        }


async def error_firewall_stats(
    db_session=None
) -> Dict[str, Any]:
    """
    获取错误防火墙统计信息

    Returns:
        统计数据，包括:
        - 总错误数
        - 总拦截数
        - 拦截率
        - 按类型分组统计
        - 最近拦截事件

    示例:
        stats = await error_firewall_stats()
        print(f"总错误数: {stats['total_errors']}")
        print(f"拦截率: {stats['block_rate']}%")
        print(f"按类型分布: {stats['by_type']}")
    """
    try:
        if not db_session:
            return {
                "success": False,
                "error": "数据库会话未提供"
            }

        firewall = get_error_firewall_service(db_session)

        stats = firewall.get_statistics()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# MCP工具定义
# ============================================

ERROR_FIREWALL_TOOLS = [
    {
        "name": "error_firewall_record",
        "description": "记录错误到错误防火墙知识库，实现'同一错误只犯一次'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_type": {
                    "type": "string",
                    "description": "错误类型 (如: ios_build, npm_install, api_call等)"
                },
                "error_scene": {
                    "type": "string",
                    "description": "错误场景的简短描述"
                },
                "error_pattern": {
                    "type": "object",
                    "description": "错误特征模式 (JSON对象，包含关键参数)"
                },
                "error_message": {
                    "type": "string",
                    "description": "完整错误信息"
                },
                "solution": {
                    "type": "string",
                    "description": "推荐的解决方案 (可选)"
                },
                "solution_confidence": {
                    "type": "number",
                    "description": "解决方案置信度 (0-1，可选)",
                    "default": 0.0
                },
                "block_level": {
                    "type": "string",
                    "enum": ["none", "warning", "block"],
                    "description": "拦截级别 (none=不拦截, warning=警告, block=强制拦截)",
                    "default": "warning"
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": "是否支持自动修复",
                    "default": False
                }
            },
            "required": ["error_type", "error_scene", "error_pattern", "error_message"]
        }
    },
    {
        "name": "error_firewall_check",
        "description": "检查操作是否应该被拦截（在执行前调用）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation_type": {
                    "type": "string",
                    "description": "操作类型"
                },
                "operation_params": {
                    "type": "object",
                    "description": "操作参数 (JSON对象)"
                },
                "session_id": {
                    "type": "string",
                    "description": "会话ID (可选)"
                }
            },
            "required": ["operation_type", "operation_params"]
        }
    },
    {
        "name": "error_firewall_query",
        "description": "查询错误防火墙中的错误记录",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_id": {
                    "type": "string",
                    "description": "错误ID (精确查询，可选)"
                },
                "error_type": {
                    "type": "string",
                    "description": "错误类型 (模糊查询，可选)"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 20
                }
            }
        }
    },
    {
        "name": "error_firewall_stats",
        "description": "获取错误防火墙统计信息（总错误数、拦截率、按类型分布等）",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]
