"""
统一的WebSocket推送工具
消除代码重复，提供统一的异步通知接口
"""

import asyncio
import threading
import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from enum import Enum

from ..common.logger import get_logger

logger = get_logger(__name__)


class NotificationPriority(Enum):
    """通知优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class UnifiedNotifier:
    """
    统一的通知推送器

    特性：
    - 自动处理异步/同步环境
    - 支持批量推送
    - 错误重试机制
    - 优先级队列
    """

    def __init__(self):
        """初始化通知器"""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._notification_queue = asyncio.Queue()
        self._retry_queue = []
        self._max_retries = 3
        self._batch_size = 10
        self._batch_timeout = 0.1  # 100ms

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            # 在同步环境中创建新的事件循环
            if not self._loop or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def notify(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        发送通知（自动处理同步/异步）

        Args:
            channel: 通知频道
            event_type: 事件类型
            data: 通知数据
            priority: 优先级
            callback: 可选的回调函数

        Returns:
            是否成功加入队列
        """
        try:
            # 检查当前是否在异步环境
            try:
                loop = asyncio.get_running_loop()
                # 在异步环境中，直接创建任务
                asyncio.create_task(
                    self._async_notify(channel, event_type, data, priority, callback)
                )
                return True
            except RuntimeError:
                # 在同步环境中，使用线程
                self._sync_notify(channel, event_type, data, priority, callback)
                return True

        except Exception as e:
            logger.error(f"通知发送失败: {e}")
            return False

    async def _async_notify(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        priority: NotificationPriority,
        callback: Optional[Callable]
    ):
        """异步发送通知"""
        try:
            from .websocket_service import notify_channel

            # 添加时间戳
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

            # 根据优先级决定是否立即发送
            if priority == NotificationPriority.CRITICAL:
                # 立即发送
                await notify_channel(channel, event_type, data)
            else:
                # 加入批处理队列
                await self._notification_queue.put({
                    "channel": channel,
                    "event_type": event_type,
                    "data": data,
                    "priority": priority.value
                })

            # 执行回调
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(True, data)
                else:
                    callback(True, data)

            logger.debug(
                f"通知已发送",
                extra={
                    "channel": channel,
                    "event_type": event_type,
                    "priority": priority.name
                }
            )

        except ImportError:
            logger.warning("WebSocket服务未启用，通知未发送")
        except Exception as e:
            logger.error(f"异步通知失败: {e}")
            # 加入重试队列
            if len(self._retry_queue) < 100:  # 限制重试队列大小
                self._retry_queue.append({
                    "channel": channel,
                    "event_type": event_type,
                    "data": data,
                    "retries": 0
                })

    def _sync_notify(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        priority: NotificationPriority,
        callback: Optional[Callable]
    ):
        """在同步环境中发送通知（使用线程）"""
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # 导入WebSocket服务
                from .websocket_service import notify_channel

                # 添加时间戳
                if "timestamp" not in data:
                    data["timestamp"] = datetime.now().isoformat()

                # 运行异步通知
                loop.run_until_complete(
                    notify_channel(channel, event_type, data)
                )

                # 执行回调
                if callback:
                    callback(True, data)

                loop.close()

            except ImportError:
                logger.debug("WebSocket服务未启用")
            except Exception as e:
                logger.debug(f"同步通知失败: {e}")
                if callback:
                    callback(False, data)

        # 启动线程
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    async def batch_notify(
        self,
        notifications: list,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> int:
        """
        批量发送通知

        Args:
            notifications: 通知列表，每项包含 (channel, event_type, data)
            priority: 优先级

        Returns:
            成功发送的数量
        """
        success_count = 0

        try:
            from .websocket_service import notify_channel

            # 按channel分组
            grouped = {}
            for channel, event_type, data in notifications:
                if channel not in grouped:
                    grouped[channel] = []
                grouped[channel].append({
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })

            # 批量发送
            for channel, messages in grouped.items():
                try:
                    # 发送批量消息
                    await notify_channel(
                        channel,
                        "batch",
                        {"messages": messages}
                    )
                    success_count += len(messages)
                except Exception as e:
                    logger.error(f"批量通知失败 (channel={channel}): {e}")

        except ImportError:
            logger.warning("WebSocket服务未启用")

        return success_count

    async def process_retry_queue(self):
        """处理重试队列"""
        if not self._retry_queue:
            return

        try:
            from .websocket_service import notify_channel

            retry_items = self._retry_queue.copy()
            self._retry_queue.clear()

            for item in retry_items:
                if item["retries"] >= self._max_retries:
                    logger.error(
                        f"通知重试次数已达上限",
                        extra={
                            "channel": item["channel"],
                            "event_type": item["event_type"]
                        }
                    )
                    continue

                try:
                    await notify_channel(
                        item["channel"],
                        item["event_type"],
                        item["data"]
                    )
                    logger.info(f"重试通知成功: {item['channel']}/{item['event_type']}")
                except Exception as e:
                    item["retries"] += 1
                    if item["retries"] < self._max_retries:
                        self._retry_queue.append(item)

        except ImportError:
            pass


# 全局通知器实例
_notifier_instance: Optional[UnifiedNotifier] = None


def get_notifier() -> UnifiedNotifier:
    """获取全局通知器实例"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = UnifiedNotifier()
    return _notifier_instance


# 便捷函数
def notify(
    channel: str,
    event_type: str,
    data: Dict[str, Any],
    priority: NotificationPriority = NotificationPriority.NORMAL
) -> bool:
    """
    快速发送通知

    Example:
        from src.mcp_core.services.unified_notifier import notify

        notify("system_stats", "update", {"cpu": 50, "memory": 60})
    """
    return get_notifier().notify(channel, event_type, data, priority)


def notify_error(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    发送错误通知

    Example:
        notify_error("DatabaseError", "Connection failed", {"host": "localhost"})
    """
    return notify(
        "error_firewall",
        "error_occurred",
        {
            "error_type": error_type,
            "message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        },
        NotificationPriority.HIGH
    )


def notify_pool_adjustment(
    old_size: int,
    new_size: int,
    reason: str
) -> bool:
    """
    发送连接池调整通知

    Example:
        notify_pool_adjustment(20, 24, "高负载扩容")
    """
    action = "扩容" if new_size > old_size else "缩容"
    return notify(
        "db_pool_stats",
        "pool_adjusted",
        {
            "action": action,
            "from": old_size,
            "to": new_size,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
    )


def notify_search_completed(
    query: str,
    top_k: int,
    duration_ms: float,
    results_count: int,
    success: bool = True
) -> bool:
    """
    发送向量检索完成通知

    Example:
        notify_search_completed("test query", 10, 156.5, 10)
    """
    return notify(
        "vector_search",
        "search_completed",
        {
            "query": query[:50],  # 限制长度
            "top_k": top_k,
            "time_ms": round(duration_ms, 2),
            "results": results_count,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
    )


async def batch_notify_stats(stats_list: list) -> int:
    """
    批量发送统计更新

    Example:
        await batch_notify_stats([
            ("system_stats", "update", {"cpu": 50}),
            ("db_pool_stats", "update", {"connections": 10})
        ])
    """
    return await get_notifier().batch_notify(stats_list)