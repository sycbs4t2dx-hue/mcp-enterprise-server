"""
多层缓存管理器
L1 (内存LRU) + L2 (Redis) + L3 (数据库/向量库)
"""

from collections import OrderedDict
from typing import Any, Optional, Dict, List, Callable
import time
import threading

from ..common.logger import get_context_logger

logger = get_context_logger(__name__)


class LRUCache:
    """线程安全的LRU缓存"""

    def __init__(self, capacity: int = 1000, ttl: int = 60):
        """
        Args:
            capacity: 最大容量
            ttl: 过期时间 (秒)
        """
        self.capacity = capacity
        self.ttl = ttl
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.lock = threading.RLock()

        # 统计信息
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            value, timestamp = self.cache[key]

            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                self.misses += 1
                return None

            # 移到末尾 (最近使用)
            self.cache.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self.lock:
            # 如果已存在，先删除
            if key in self.cache:
                del self.cache[key]

            # 添加新值 (带时间戳)
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)

            # 超过容量，删除最旧的
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0

            return {
                "capacity": self.capacity,
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.2%}",
                "utilization": f"{len(self.cache) / self.capacity:.2%}"
            }


class MultiLevelCache:
    """
    多层缓存管理器
    L1 (内存) → L2 (Redis) → L3 (数据库)
    """

    def __init__(
        self,
        l1_capacity: int = 1000,
        l1_ttl: int = 60,
        l2_ttl: int = 300,
        redis_client: Optional[Any] = None
    ):
        """
        Args:
            l1_capacity: L1缓存容量
            l1_ttl: L1缓存TTL (秒)
            l2_ttl: L2缓存TTL (秒)
            redis_client: Redis客户端 (可选)
        """
        # L1缓存 (内存LRU)
        self.l1_cache = LRUCache(capacity=l1_capacity, ttl=l1_ttl)

        # L2缓存 (Redis)
        self.redis_client = redis_client
        self.l2_ttl = l2_ttl

        # 缓存键前缀
        self.key_prefix = "mlc:"  # Multi-Level Cache

        logger.info(
            "多层缓存初始化完成",
            extra={
                "l1_capacity": l1_capacity,
                "l1_ttl": l1_ttl,
                "l2_ttl": l2_ttl,
                "redis_enabled": redis_client is not None
            }
        )

    def get(self, key: str, l3_loader: Optional[Callable] = None) -> Optional[Any]:
        """
        多层缓存获取

        Args:
            key: 缓存键
            l3_loader: L3数据加载函数 (lambda: load_from_db())

        Returns:
            缓存值，所有层级均未命中返回None
        """
        # L1: 内存缓存
        value = self.l1_cache.get(key)
        if value is not None:
            logger.debug(f"L1缓存命中: {key}")
            return value

        # L2: Redis缓存
        if self.redis_client:
            cache_key = f"{self.key_prefix}{key}"
            try:
                value = self.redis_client._redis_get_raw(cache_key)
                if value is not None:
                    logger.debug(f"L2缓存命中: {key}")
                    # 回填L1
                    self.l1_cache.set(key, value)
                    return value
            except Exception as e:
                logger.warning(f"L2缓存查询失败: {e}")

        # L3: 数据加载器
        if l3_loader:
            try:
                value = l3_loader()
                if value is not None:
                    logger.debug(f"L3加载成功: {key}")
                    # 回填L2和L1
                    self.set(key, value)
                    return value
            except Exception as e:
                logger.error(f"L3加载失败: {e}")
                return None

        logger.debug(f"所有层级未命中: {key}")
        return None

    def set(self, key: str, value: Any, l2_ttl: Optional[int] = None) -> None:
        """
        设置多层缓存

        Args:
            key: 缓存键
            value: 缓存值
            l2_ttl: L2 TTL (可选，覆盖默认值)
        """
        # 设置L1
        self.l1_cache.set(key, value)

        # 设置L2
        if self.redis_client:
            cache_key = f"{self.key_prefix}{key}"
            ttl = l2_ttl if l2_ttl is not None else self.l2_ttl
            try:
                import json
                serialized = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.redis_client.client.setex(cache_key, ttl, serialized)
            except Exception as e:
                logger.warning(f"L2缓存设置失败: {e}")

        logger.debug(f"多层缓存设置成功: {key}")

    def delete(self, key: str) -> None:
        """删除多层缓存"""
        # 删除L1
        self.l1_cache.delete(key)

        # 删除L2
        if self.redis_client:
            cache_key = f"{self.key_prefix}{key}"
            try:
                self.redis_client.client.delete(cache_key)
            except Exception as e:
                logger.warning(f"L2缓存删除失败: {e}")

        logger.debug(f"多层缓存删除: {key}")

    def invalidate_pattern(self, pattern: str) -> int:
        """
        根据模式清除缓存

        Args:
            pattern: 键模式 (如 "user:*")

        Returns:
            清除的L2缓存数量 (L1无法按模式清除)
        """
        # L1: 暴力清空 (无法按模式清除)
        self.l1_cache.clear()

        # L2: Redis支持模式清除
        count = 0
        if self.redis_client:
            try:
                cache_pattern = f"{self.key_prefix}{pattern}"
                keys = self.redis_client.client.keys(cache_pattern)
                if keys:
                    count = self.redis_client.client.delete(*keys)
            except Exception as e:
                logger.warning(f"L2模式清除失败: {e}")

        logger.info(f"模式清除缓存: {pattern}, L2清除数量: {count}")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        l1_stats = self.l1_cache.get_stats()

        return {
            "l1_memory": l1_stats,
            "redis_enabled": self.redis_client is not None
        }

    def warmup(self, keys: List[str], loader: Callable[[str], Any]) -> int:
        """
        缓存预热

        Args:
            keys: 要预热的键列表
            loader: 数据加载函数 (key) -> value

        Returns:
            预热成功数量
        """
        success_count = 0

        for key in keys:
            try:
                value = loader(key)
                if value is not None:
                    self.set(key, value)
                    success_count += 1
            except Exception as e:
                logger.error(f"预热失败: {key}, 错误: {e}")
                continue

        logger.info(f"缓存预热完成: {success_count}/{len(keys)}")
        return success_count
