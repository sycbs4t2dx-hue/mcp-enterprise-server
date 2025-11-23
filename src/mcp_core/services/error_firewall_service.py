"""
错误防火墙服务
实现"同一错误只犯一次"的智能错误防护系统
"""

import hashlib
import json
import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..common.logger import get_logger

logger = get_logger(__name__)


class ErrorFirewallService:
    """错误防火墙核心服务"""

    def __init__(self, db_session: Session):
        """
        初始化错误防火墙服务

        Args:
            db_session: 数据库会话
        """
        self.db_session = db_session
        logger.info("错误防火墙服务初始化完成")

    # ============================================
    # 错误记录管理
    # ============================================

    def record_error(
        self,
        error_type: str,
        error_scene: str,
        error_pattern: Dict[str, Any],
        error_message: str,
        solution: Optional[str] = None,
        solution_confidence: float = 0.0,
        block_level: str = "warning",
        auto_fix: bool = False,
        project_id: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录新错误到知识库

        Args:
            error_type: 错误类型 (ios_build/npm_install等)
            error_scene: 错误场景描述
            error_pattern: 错误特征模式
            error_message: 原始错误信息
            solution: 推荐解决方案
            solution_confidence: 解决方案置信度
            block_level: 拦截级别 (none/warning/block)
            auto_fix: 是否支持自动修复
            project_id: 关联项目ID
            created_by: 创建者

        Returns:
            记录结果
        """
        try:
            # 生成错误唯一标识
            error_id = self._generate_error_id(error_type, error_pattern)

            # 检查是否已存在
            existing = self.get_error_by_id(error_id)
            if existing:
                # 更新发生次数
                return self._update_error_occurrence(error_id)

            # 插入新错误记录
            query = text("""
                INSERT INTO error_records (
                    error_id, error_type, error_scene, error_pattern,
                    error_message, solution, solution_confidence,
                    block_level, auto_fix, project_id, created_by,
                    last_occurred_at
                ) VALUES (
                    :error_id, :error_type, :error_scene, :error_pattern,
                    :error_message, :solution, :solution_confidence,
                    :block_level, :auto_fix, :project_id, :created_by,
                    NOW()
                )
            """)

            self.db_session.execute(query, {
                "error_id": error_id,
                "error_type": error_type,
                "error_scene": error_scene,
                "error_pattern": json.dumps(error_pattern, ensure_ascii=False),
                "error_message": error_message,
                "solution": solution,
                "solution_confidence": solution_confidence,
                "block_level": block_level,
                "auto_fix": auto_fix,
                "project_id": project_id,
                "created_by": created_by
            })
            self.db_session.commit()

            logger.info(
                f"错误已记录",
                extra={"error_id": error_id, "error_type": error_type}
            )

            # 推送WebSocket通知
            self._notify_error_recorded(error_id, error_type, error_scene, solution)

            return {
                "success": True,
                "error_id": error_id,
                "message": "错误已成功记录到知识库",
                "is_new": True
            }

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"记录错误失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_error_by_id(self, error_id: str) -> Optional[Dict[str, Any]]:
        """
        根据错误ID获取错误记录

        Args:
            error_id: 错误唯一标识

        Returns:
            错误记录或None
        """
        try:
            query = text("""
                SELECT * FROM error_records WHERE error_id = :error_id
            """)
            result = self.db_session.execute(query, {"error_id": error_id}).fetchone()

            if result:
                return dict(result._mapping)
            return None

        except Exception as e:
            logger.error(f"获取错误记录失败: {e}")
            return None

    def _update_error_occurrence(self, error_id: str) -> Dict[str, Any]:
        """更新错误发生次数"""
        try:
            query = text("""
                UPDATE error_records
                SET occurrence_count = occurrence_count + 1,
                    last_occurred_at = NOW()
                WHERE error_id = :error_id
            """)
            self.db_session.execute(query, {"error_id": error_id})
            self.db_session.commit()

            return {
                "success": True,
                "error_id": error_id,
                "message": "错误发生次数已更新",
                "is_new": False
            }

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"更新错误次数失败: {e}")
            return {"success": False, "error": str(e)}

    # ============================================
    # 错误检测与拦截
    # ============================================

    def check_operation(
        self,
        operation_type: str,
        operation_params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检查操作是否应该被拦截

        Args:
            operation_type: 操作类型
            operation_params: 操作参数
            session_id: 会话ID

        Returns:
            检查结果 (should_block, matched_error, solution等)
        """
        try:
            # 生成操作特征
            operation_pattern = {
                "operation": operation_type,
                **operation_params
            }

            # 搜索匹配的错误
            matches = self._find_matching_errors(operation_type, operation_params)

            if not matches:
                return {
                    "should_block": False,
                    "risk_level": "low",
                    "message": "操作安全，无匹配的历史错误"
                }

            # 获取最高置信度的匹配
            best_match = max(matches, key=lambda x: x["match_confidence"])

            # 判断是否拦截
            should_block = best_match["block_level"] == "block"
            should_warn = best_match["block_level"] == "warning"

            # 记录拦截日志
            self._log_intercept(
                error_record_id=best_match["id"],
                intercept_type="before",
                intercept_action="blocked" if should_block else ("warned" if should_warn else "passed"),
                operation_type=operation_type,
                operation_params=operation_params,
                match_confidence=best_match["match_confidence"],
                session_id=session_id
            )

            # 推送WebSocket通知
            if should_block or should_warn:
                self._notify_error_intercepted(
                    best_match["error_id"],
                    operation_type,
                    best_match["solution"],
                    "blocked" if should_block else "warned"
                )

            return {
                "should_block": should_block,
                "should_warn": should_warn,
                "risk_level": "high" if should_block else ("medium" if should_warn else "low"),
                "matched_error": {
                    "error_id": best_match["error_id"],
                    "error_type": best_match["error_type"],
                    "error_scene": best_match["error_scene"],
                    "match_confidence": best_match["match_confidence"]
                },
                "solution": best_match["solution"],
                "solution_confidence": best_match["solution_confidence"],
                "auto_fix_available": best_match["auto_fix"],
                "message": f"⚠️ 检测到历史错误: {best_match['error_scene']}" if (should_block or should_warn) else "操作已通过检查"
            }

        except Exception as e:
            logger.error(f"检查操作失败: {e}")
            return {
                "should_block": False,
                "risk_level": "unknown",
                "error": str(e)
            }

    def _find_matching_errors(
        self,
        operation_type: str,
        operation_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        查找匹配的历史错误

        Args:
            operation_type: 操作类型
            operation_params: 操作参数

        Returns:
            匹配的错误列表 (带置信度)
        """
        try:
            # 查询同类型的错误
            query = text("""
                SELECT id, error_id, error_type, error_scene, error_pattern,
                       solution, solution_confidence, block_level, auto_fix
                FROM error_records
                WHERE error_type = :error_type
                  AND block_level != 'none'
            """)
            results = self.db_session.execute(
                query, {"error_type": operation_type}
            ).fetchall()

            matches = []
            for row in results:
                record = dict(row._mapping)
                stored_pattern = json.loads(record["error_pattern"])

                # 计算特征匹配度
                confidence = self._calculate_match_confidence(
                    operation_params, stored_pattern
                )

                if confidence > 0.5:  # 置信度阈值
                    record["match_confidence"] = confidence
                    matches.append(record)

            return matches

        except Exception as e:
            logger.error(f"查找匹配错误失败: {e}")
            return []

    def _calculate_match_confidence(
        self,
        operation_params: Dict[str, Any],
        stored_pattern: Dict[str, Any]
    ) -> float:
        """
        计算操作与存储模式的匹配置信度

        Args:
            operation_params: 当前操作参数
            stored_pattern: 存储的错误模式

        Returns:
            置信度 (0-1)
        """
        if not stored_pattern:
            return 0.0

        matched_keys = 0
        total_keys = len(stored_pattern)

        for key, value in stored_pattern.items():
            if key in operation_params:
                if operation_params[key] == value:
                    matched_keys += 1
                elif str(operation_params[key]).lower() == str(value).lower():
                    matched_keys += 0.8

        return matched_keys / total_keys if total_keys > 0 else 0.0

    # ============================================
    # 拦截日志
    # ============================================

    def _log_intercept(
        self,
        error_record_id: int,
        intercept_type: str,
        intercept_action: str,
        operation_type: str,
        operation_params: Dict[str, Any],
        match_confidence: float,
        session_id: Optional[str] = None
    ):
        """记录拦截日志"""
        try:
            query = text("""
                INSERT INTO error_intercept_logs (
                    error_record_id, intercept_type, intercept_action,
                    operation_type, operation_params, match_confidence,
                    session_id
                ) VALUES (
                    :error_record_id, :intercept_type, :intercept_action,
                    :operation_type, :operation_params, :match_confidence,
                    :session_id
                )
            """)
            self.db_session.execute(query, {
                "error_record_id": error_record_id,
                "intercept_type": intercept_type,
                "intercept_action": intercept_action,
                "operation_type": operation_type,
                "operation_params": json.dumps(operation_params, ensure_ascii=False),
                "match_confidence": match_confidence,
                "session_id": session_id
            })
            self.db_session.commit()

            # 更新拦截计数
            if intercept_action == "blocked":
                self._update_blocked_count(error_record_id)

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"记录拦截日志失败: {e}")

    def _update_blocked_count(self, error_record_id: int):
        """更新错误的拦截计数"""
        try:
            query = text("""
                UPDATE error_records
                SET blocked_count = blocked_count + 1
                WHERE id = :id
            """)
            self.db_session.execute(query, {"id": error_record_id})
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"更新拦截计数失败: {e}")

    # ============================================
    # 统计查询
    # ============================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取错误防火墙统计信息

        Returns:
            统计数据
        """
        try:
            # 总体统计
            query = text("""
                SELECT
                    COUNT(*) as total_errors,
                    SUM(occurrence_count) as total_occurrences,
                    SUM(blocked_count) as total_blocks,
                    AVG(solution_confidence) as avg_confidence,
                    COUNT(CASE WHEN block_level = 'block' THEN 1 END) as blocking_errors,
                    COUNT(CASE WHEN auto_fix = TRUE THEN 1 END) as auto_fixable
                FROM error_records
            """)
            stats = self.db_session.execute(query).fetchone()

            # 按类型统计
            type_query = text("""
                SELECT error_type, COUNT(*) as count, SUM(blocked_count) as blocks
                FROM error_records
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 10
            """)
            type_stats = self.db_session.execute(type_query).fetchall()

            # 最近拦截
            recent_query = text("""
                SELECT el.*, er.error_scene, er.solution
                FROM error_intercept_logs el
                JOIN error_records er ON el.error_record_id = er.id
                ORDER BY el.created_at DESC
                LIMIT 10
            """)
            recent_intercepts = self.db_session.execute(recent_query).fetchall()

            return {
                "total_errors": stats.total_errors or 0,
                "total_occurrences": int(stats.total_occurrences or 0),
                "total_blocks": int(stats.total_blocks or 0),
                "avg_confidence": round(float(stats.avg_confidence or 0), 2),
                "blocking_errors": stats.blocking_errors or 0,
                "auto_fixable": stats.auto_fixable or 0,
                "block_rate": round(
                    (stats.total_blocks / stats.total_occurrences * 100)
                    if stats.total_occurrences else 0, 2
                ),
                "by_type": [
                    {"type": r.error_type, "count": r.count, "blocks": int(r.blocks or 0)}
                    for r in type_stats
                ],
                "recent_intercepts": [
                    {
                        "id": r.id,
                        "error_scene": r.error_scene,
                        "action": r.intercept_action,
                        "confidence": float(r.match_confidence),
                        "solution": r.solution,
                        "time": r.created_at.isoformat() if r.created_at else None
                    }
                    for r in recent_intercepts
                ]
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近的错误记录

        Args:
            limit: 返回数量

        Returns:
            错误记录列表
        """
        try:
            query = text("""
                SELECT id, error_id, error_type, error_scene, solution,
                       solution_confidence, block_level, occurrence_count,
                       blocked_count, last_occurred_at, created_at
                FROM error_records
                ORDER BY last_occurred_at DESC
                LIMIT :limit
            """)
            results = self.db_session.execute(query, {"limit": limit}).fetchall()

            return [
                {
                    "id": r.id,
                    "error_id": r.error_id,
                    "error_type": r.error_type,
                    "error_scene": r.error_scene,
                    "solution": r.solution,
                    "confidence": float(r.solution_confidence or 0),
                    "block_level": r.block_level,
                    "occurrences": r.occurrence_count,
                    "blocks": r.blocked_count,
                    "last_occurred": r.last_occurred_at.isoformat() if r.last_occurred_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"获取最近错误失败: {e}")
            return []

    # ============================================
    # 辅助方法
    # ============================================

    def _generate_error_id(
        self,
        error_type: str,
        error_pattern: Dict[str, Any]
    ) -> str:
        """
        生成错误唯一标识

        Args:
            error_type: 错误类型
            error_pattern: 错误特征模式

        Returns:
            错误ID (Hash)
        """
        # 排序键以确保一致性
        sorted_pattern = json.dumps(error_pattern, sort_keys=True, ensure_ascii=False)
        content = f"{error_type}:{sorted_pattern}"
        return hashlib.md5(content.encode()).hexdigest()

    # ============================================
    # WebSocket通知
    # ============================================

    def _notify_error_recorded(
        self,
        error_id: str,
        error_type: str,
        error_scene: str,
        solution: Optional[str]
    ):
        """推送错误记录通知"""
        try:
            from .websocket_service import notify_channel, Channels

            def async_notify():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        notify_channel(
                            Channels.ERROR_FIREWALL,
                            "error_recorded",
                            {
                                "error_id": error_id,
                                "error_type": error_type,
                                "error_scene": error_scene,
                                "solution": solution,
                                "status": "recorded"
                            }
                        )
                    )
                    loop.close()
                except Exception as e:
                    logger.debug(f"WebSocket推送失败: {e}")

            threading.Thread(target=async_notify, daemon=True).start()
        except ImportError:
            pass

    def _notify_error_intercepted(
        self,
        error_id: str,
        operation_type: str,
        solution: Optional[str],
        action: str
    ):
        """推送错误拦截通知"""
        try:
            from .websocket_service import notify_channel, Channels

            def async_notify():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        notify_channel(
                            Channels.ERROR_FIREWALL,
                            "error_intercepted",
                            {
                                "error_id": error_id,
                                "operation_type": operation_type,
                                "solution": solution,
                                "action": action,
                                "status": "intercepted"
                            }
                        )
                    )
                    loop.close()
                except Exception as e:
                    logger.debug(f"WebSocket推送失败: {e}")

            threading.Thread(target=async_notify, daemon=True).start()
        except ImportError:
            pass


# ============================================
# 单例模式
# ============================================
_error_firewall_instance: Optional[ErrorFirewallService] = None


def get_error_firewall_service(db_session: Session = None) -> ErrorFirewallService:
    """
    获取错误防火墙服务单例

    Args:
        db_session: 数据库会话

    Returns:
        ErrorFirewallService实例
    """
    global _error_firewall_instance

    if _error_firewall_instance is None:
        if db_session is None:
            raise ValueError("首次创建错误防火墙服务需要提供db_session")
        _error_firewall_instance = ErrorFirewallService(db_session)

    return _error_firewall_instance
