"""
动态数据库连接池管理器
基于负载自动调整pool_size和max_overflow
"""

import time
import threading
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from ..common.logger import get_context_logger
from ..common.config import get_settings

logger = get_context_logger(__name__)


@dataclass
class PoolMetrics:
    """连接池指标"""
    size: int = 0               # 当前池大小
    checked_out: int = 0        # 已签出连接数
    checked_in: int = 0         # 已签入连接数
    overflow: int = 0           # 溢出连接数
    total_connections: int = 0  # 总连接数
    
    # 统计指标
    qps: float = 0.0            # 每秒查询数
    avg_wait_time: float = 0.0  # 平均等待时间 (ms)
    utilization: float = 0.0    # 使用率 (%)
    
    # 告警指标
    connection_timeouts: int = 0   # 连接超时次数
    connection_errors: int = 0     # 连接错误次数
    potential_leaks: int = 0       # 疑似泄漏连接数


class DynamicConnectionPoolManager:
    """动态连接池管理器"""
    
    def __init__(
        self,
        database_url: str,
        min_pool_size: int = 5,
        max_pool_size: int = 100,
        min_overflow: int = 5,
        max_overflow: int = 50,
        adjustment_interval: int = 60,  # 调整间隔 (秒)
        cooldown_period: int = 300      # 冷却期 (秒)
    ):
        """
        Args:
            database_url: 数据库连接URL
            min_pool_size: 最小池大小
            max_pool_size: 最大池大小
            min_overflow: 最小溢出
            max_overflow: 最大溢出
            adjustment_interval: 调整检查间隔
            cooldown_period: 调整后冷却期
        """
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.min_overflow = min_overflow
        self.max_overflow = max_overflow
        self.adjustment_interval = adjustment_interval
        self.cooldown_period = cooldown_period
        
        # 当前配置
        self.current_pool_size = min_pool_size
        self.current_max_overflow = min_overflow
        
        # 创建引擎
        self.engine: Optional[Engine] = None
        self._create_engine()
        
        # 监控数据
        self.metrics = PoolMetrics()
        self.query_times: list = []  # 最近1000次查询时间
        self.last_adjustment_time: Optional[datetime] = None
        
        # 监控线程
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # 统计计数器
        self.total_queries = 0
        self.start_time = time.time()
        
        logger.info(
            "动态连接池初始化完成",
            extra={
                "min_pool_size": min_pool_size,
                "max_pool_size": max_pool_size,
                "current_pool_size": self.current_pool_size
            }
        )
    
    def _create_engine(self) -> None:
        """创建数据库引擎"""
        settings = get_settings()
        
        self.engine = create_engine(
            self.database_url,
            pool_size=self.current_pool_size,
            max_overflow=self.current_max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
            poolclass=pool.QueuePool,
            echo=False
        )
        
        # 注册事件监听器
        self._register_event_listeners()
    
    def _register_event_listeners(self) -> None:
        """注册SQLAlchemy事件监听器"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """连接创建事件"""
            logger.debug("数据库连接创建")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """连接签出事件"""
            connection_record.checkout_time = time.time()
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """连接签入事件"""
            if hasattr(connection_record, 'checkout_time'):
                duration = time.time() - connection_record.checkout_time
                self.query_times.append(duration)
                
                # 保留最近1000次
                if len(self.query_times) > 1000:
                    self.query_times.pop(0)
                
                self.total_queries += 1
    
    def start_monitoring(self) -> None:
        """启动监控线程"""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.stop_monitoring.clear()
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="DBPoolMonitor"
            )
            self.monitoring_thread.start()
            logger.info("连接池监控已启动")
    
    def stop(self) -> None:
        """停止监控并关闭引擎"""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.engine:
            self.engine.dispose()
        
        logger.info("动态连接池已停止")
    
    def _monitoring_loop(self) -> None:
        """监控循环"""
        while not self.stop_monitoring.is_set():
            try:
                # 更新指标
                self._update_metrics()

                # 推送连接池统计 (每次监控循环都推送)
                self._broadcast_pool_stats()

                # 检查是否需要调整
                if self._should_adjust():
                    self._adjust_pool_size()

                # 检查告警
                self._check_alerts()

            except Exception as e:
                logger.error(f"连接池监控异常: {e}")

            # 等待下一次检查
            self.stop_monitoring.wait(self.adjustment_interval)
    
    def _update_metrics(self) -> None:
        """更新连接池指标"""
        if not self.engine:
            return
        
        pool_obj: Pool = self.engine.pool
        
        # 基础指标
        self.metrics.size = pool_obj.size()
        self.metrics.checked_out = pool_obj.checkedout()
        self.metrics.checked_in = pool_obj.checkedin()
        self.metrics.overflow = pool_obj.overflow()
        self.metrics.total_connections = self.metrics.size + self.metrics.overflow
        
        # 计算使用率
        if self.metrics.size > 0:
            self.metrics.utilization = (self.metrics.checked_out / self.metrics.size) * 100
        
        # 计算QPS
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.metrics.qps = self.total_queries / elapsed
        
        # 计算平均等待时间
        if self.query_times:
            self.metrics.avg_wait_time = (sum(self.query_times) / len(self.query_times)) * 1000
        
        logger.debug(
            "连接池指标更新",
            extra={
                "size": self.metrics.size,
                "checked_out": self.metrics.checked_out,
                "utilization": f"{self.metrics.utilization:.1f}%",
                "qps": f"{self.metrics.qps:.2f}"
            }
        )

    def _broadcast_pool_stats(self) -> None:
        """通过WebSocket广播连接池统计"""
        try:
            from .websocket_service import notify_channel, Channels

            def async_broadcast():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        notify_channel(
                            Channels.DB_POOL_STATS,
                            "stats_update",
                            {
                                "pool_size": self.current_pool_size,
                                "active_connections": self.metrics.checked_out,
                                "idle_connections": self.metrics.checked_in,
                                "overflow_connections": self.metrics.overflow,
                                "utilization": round(self.metrics.utilization, 2),
                                "qps": round(self.metrics.qps, 2),
                                "avg_query_time": round(self.metrics.avg_wait_time, 2),
                                "max_wait_time": 0,
                                "total_queries": self.total_queries,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                    )
                    loop.close()
                except Exception as e:
                    logger.debug(f"广播连接池统计失败: {e}")

            threading.Thread(target=async_broadcast, daemon=True).start()

        except ImportError:
            pass
    
    def _should_adjust(self) -> bool:
        """判断是否应该调整池大小"""
        # 冷却期检查
        if self.last_adjustment_time:
            elapsed = (datetime.now() - self.last_adjustment_time).total_seconds()
            if elapsed < self.cooldown_period:
                return False
        
        # 使用率判断
        if self.metrics.utilization > 80:  # 高负载
            return True
        elif self.metrics.utilization < 20:  # 低负载
            return True
        
        # 溢出检查
        if self.metrics.overflow > 0:  # 有溢出连接
            return True
        
        return False
    
    def _adjust_pool_size(self) -> None:
        """动态调整池大小"""
        old_size = self.current_pool_size
        new_size = old_size
        reason = ""
        
        # 调整策略
        if self.metrics.utilization > 80:
            # 高负载：扩容20%
            new_size = min(int(old_size * 1.2), self.max_pool_size)
            reason = "高负载扩容"
        
        elif self.metrics.utilization < 20 and old_size > self.min_pool_size:
            # 低负载：缩容20%
            new_size = max(int(old_size * 0.8), self.min_pool_size)
            reason = "低负载缩容"
        
        elif self.metrics.overflow > 0:
            # 有溢出：扩容30%
            new_size = min(int(old_size * 1.3), self.max_pool_size)
            reason = "溢出扩容"
        
        else:
            return  # 无需调整
        
        # 执行调整
        if new_size != old_size:
            self._resize_pool(new_size)
            self.last_adjustment_time = datetime.now()

            logger.info(
                f"连接池已调整: {old_size} → {new_size}",
                extra={
                    "reason": reason,
                    "utilization": f"{self.metrics.utilization:.1f}%",
                    "qps": f"{self.metrics.qps:.2f}"
                }
            )

            # WebSocket实时推送 (Phase 4集成)
            self._notify_pool_adjustment(old_size, new_size, reason)

    def _notify_pool_adjustment(self, old_size: int, new_size: int, reason: str) -> None:
        """通过WebSocket推送连接池调整通知"""
        try:
            from .websocket_service import notify_channel, Channels

            # 判断操作类型
            action = "扩容" if new_size > old_size else "缩容"

            # 在新线程中异步执行
            def async_notify():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # 推送调整历史事件
                    loop.run_until_complete(
                        notify_channel(
                            Channels.DB_POOL_STATS,
                            "pool_adjusted",
                            {
                                "action": action,
                                "from": old_size,
                                "to": new_size,
                                "reason": reason,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                    )

                    # 推送完整的连接池统计
                    loop.run_until_complete(
                        notify_channel(
                            Channels.DB_POOL_STATS,
                            "stats_update",
                            {
                                "pool_size": new_size,
                                "active_connections": self.metrics.checked_out,
                                "idle_connections": self.metrics.checked_in,
                                "overflow_connections": self.metrics.overflow,
                                "utilization": round(self.metrics.utilization, 2),
                                "qps": round(self.metrics.qps, 2),
                                "avg_query_time": round(self.metrics.avg_wait_time, 2),
                                "max_wait_time": 0,  # TODO: 实现max_wait_time追踪
                                "total_queries": self.total_queries,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                    )

                    loop.close()
                except Exception as e:
                    logger.debug(f"WebSocket推送失败: {e}")

            # 在后台线程执行
            threading.Thread(target=async_notify, daemon=True).start()

        except ImportError:
            # WebSocket服务未启用,静默跳过
            pass

    def _resize_pool(self, new_size: int) -> None:
        """重建连接池 (新大小)"""
        if not self.engine:
            return
        
        # 保存旧引擎
        old_engine = self.engine
        
        # 更新配置
        self.current_pool_size = new_size
        
        # 创建新引擎
        self._create_engine()
        
        # 销毁旧引擎
        old_engine.dispose()
    
    def _check_alerts(self) -> None:
        """检查告警条件"""
        # 池饱和告警
        if self.metrics.utilization > 90:
            logger.warning(
                f"连接池接近饱和",
                extra={
                    "utilization": f"{self.metrics.utilization:.1f}%",
                    "size": self.metrics.size,
                    "checked_out": self.metrics.checked_out
                }
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        self._update_metrics()
        
        return {
            "pool_config": {
                "current_size": self.current_pool_size,
                "min_size": self.min_pool_size,
                "max_size": self.max_pool_size,
                "max_overflow": self.current_max_overflow
            },
            "current_metrics": {
                "size": self.metrics.size,
                "checked_out": self.metrics.checked_out,
                "checked_in": self.metrics.checked_in,
                "overflow": self.metrics.overflow,
                "total_connections": self.metrics.total_connections,
                "utilization": f"{self.metrics.utilization:.2f}%"
            },
            "performance": {
                "qps": f"{self.metrics.qps:.2f}",
                "avg_wait_time_ms": f"{self.metrics.avg_wait_time:.2f}",
                "total_queries": self.total_queries,
                "uptime_seconds": int(time.time() - self.start_time)
            },
            "alerts": {
                "potential_leaks": self.metrics.potential_leaks,
                "connection_timeouts": self.metrics.connection_timeouts,
                "connection_errors": self.metrics.connection_errors
            }
        }


# 全局实例
_dynamic_pool_manager: Optional[DynamicConnectionPoolManager] = None


def get_dynamic_pool_manager() -> DynamicConnectionPoolManager:
    """获取动态连接池管理器单例"""
    global _dynamic_pool_manager
    
    if _dynamic_pool_manager is None:
        settings = get_settings()
        _dynamic_pool_manager = DynamicConnectionPoolManager(
            database_url=settings.database.url,
            min_pool_size=5,
            max_pool_size=100,
            min_overflow=5,
            max_overflow=50
        )
        _dynamic_pool_manager.start_monitoring()
    
    return _dynamic_pool_manager
