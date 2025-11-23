"""
缓存集成模块
激活并集成多级缓存到现有系统
"""

from typing import Any, Dict, Optional, Callable
import json
import hashlib
from functools import wraps

from .multi_level_cache import MultiLevelCache
from .redis_client import get_redis_client
from ..common.logger import get_logger

logger = get_logger(__name__)


class CacheIntegration:
    """
    缓存集成管理器

    提供：
    - 多级缓存激活
    - 装饰器支持
    - 自动键生成
    - 缓存预热
    """

    def __init__(self):
        """初始化缓存集成"""
        # 获取Redis客户端
        try:
            redis_client = get_redis_client()
            logger.info("Redis缓存层已启用")
        except Exception as e:
            redis_client = None
            logger.warning(f"Redis不可用，仅使用内存缓存: {e}")

        # 创建多级缓存实例
        self.cache = MultiLevelCache(
            l1_capacity=2000,  # 内存缓存2000个键
            l1_ttl=60,         # 内存缓存60秒
            l2_ttl=300,        # Redis缓存300秒
            redis_client=redis_client
        )

        # 缓存策略配置
        self.cache_configs = {
            # MCP工具结果缓存
            "mcp_tools": {
                "ttl": 30,
                "prefix": "mcp:tools:",
                "enabled": True
            },
            # 向量检索结果缓存
            "vector_search": {
                "ttl": 120,
                "prefix": "vec:search:",
                "enabled": True
            },
            # 数据库查询缓存
            "db_query": {
                "ttl": 60,
                "prefix": "db:query:",
                "enabled": True
            },
            # 统计数据缓存
            "stats": {
                "ttl": 10,
                "prefix": "stats:",
                "enabled": True
            },
            # 错误解决方案缓存
            "error_solutions": {
                "ttl": 600,
                "prefix": "error:sol:",
                "enabled": True
            }
        }

        logger.info("缓存集成初始化完成", extra={"configs": list(self.cache_configs.keys())})

    def generate_cache_key(self, category: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            category: 缓存类别
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            生成的缓存键
        """
        config = self.cache_configs.get(category, {})
        prefix = config.get("prefix", f"{category}:")

        # 构建键内容
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        key_content = ":".join(key_parts)

        # 如果太长，使用hash
        if len(key_content) > 100:
            key_content = hashlib.md5(key_content.encode()).hexdigest()

        return f"{prefix}{key_content}"

    def cached(
        self,
        category: str = "default",
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """
        缓存装饰器

        Args:
            category: 缓存类别
            ttl: 自定义TTL
            key_func: 自定义键生成函数

        Example:
            @cache_integration.cached(category="vector_search", ttl=120)
            async def search_vectors(query, top_k=10):
                # 执行向量检索
                return results
        """
        def decorator(func):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 检查是否启用缓存
                config = self.cache_configs.get(category, {})
                if not config.get("enabled", True):
                    return func(*args, **kwargs)

                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self.generate_cache_key(category, *args, **kwargs)

                # 尝试从缓存获取
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value

                # 执行原函数
                result = func(*args, **kwargs)

                # 存入缓存
                if result is not None:
                    cache_ttl = ttl or config.get("ttl", 60)
                    self.cache.set(cache_key, result, l2_ttl=cache_ttl)
                    logger.debug(f"缓存设置: {cache_key} (TTL={cache_ttl})")

                return result

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 检查是否启用缓存
                config = self.cache_configs.get(category, {})
                if not config.get("enabled", True):
                    return await func(*args, **kwargs)

                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self.generate_cache_key(category, *args, **kwargs)

                # 尝试从缓存获取
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value

                # 执行原函数
                result = await func(*args, **kwargs)

                # 存入缓存
                if result is not None:
                    cache_ttl = ttl or config.get("ttl", 60)
                    self.cache.set(cache_key, result, l2_ttl=cache_ttl)
                    logger.debug(f"缓存设置: {cache_key} (TTL={cache_ttl})")

                return result

            # 根据函数类型返回相应的包装器
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def get_or_load(
        self,
        key: str,
        loader: Callable,
        category: str = "default",
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取或加载缓存

        Args:
            key: 缓存键
            loader: 数据加载函数
            category: 缓存类别
            ttl: TTL覆盖

        Returns:
            缓存值或加载的值
        """
        # 添加类别前缀
        config = self.cache_configs.get(category, {})
        full_key = f"{config.get('prefix', '')}{key}"

        # 使用多级缓存的get方法
        return self.cache.get(full_key, loader)

    def invalidate_category(self, category: str) -> int:
        """
        清除某个类别的所有缓存

        Args:
            category: 缓存类别

        Returns:
            清除的缓存数量
        """
        config = self.cache_configs.get(category, {})
        prefix = config.get("prefix", f"{category}:")
        pattern = f"{prefix}*"

        count = self.cache.invalidate_pattern(pattern)
        logger.info(f"清除缓存类别: {category}, 数量: {count}")

        return count

    def preload_cache(self, preload_data: Dict[str, Any]):
        """
        预加载缓存

        Args:
            preload_data: 预加载数据 {key: value}
        """
        for key, value in preload_data.items():
            self.cache.set(key, value)

        logger.info(f"预加载缓存完成: {len(preload_data)}个键")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        l1_stats = self.cache.l1_cache.get_stats()

        # L2统计（如果Redis可用）
        l2_stats = {}
        if self.cache.redis_client:
            try:
                info = self.cache.redis_client.client.info("stats")
                l2_stats = {
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": round(
                        info.get("keyspace_hits", 0) /
                        max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100,
                        2
                    )
                }
            except Exception as e:
                logger.error(f"获取Redis统计失败: {e}")

        return {
            "l1_cache": l1_stats,
            "l2_cache": l2_stats,
            "cache_configs": self.cache_configs
        }

    def clear_all(self):
        """清除所有缓存"""
        # 清除L1
        self.cache.l1_cache.clear()

        # 清除L2
        if self.cache.redis_client:
            try:
                # 清除所有多级缓存键
                pattern = f"{self.cache.key_prefix}*"
                keys = self.cache.redis_client.client.keys(pattern)
                if keys:
                    self.cache.redis_client.client.delete(*keys)
                    logger.info(f"清除L2缓存: {len(keys)}个键")
            except Exception as e:
                logger.error(f"清除L2缓存失败: {e}")

        logger.info("所有缓存已清除")


# 全局缓存集成实例
_cache_integration: Optional[CacheIntegration] = None


def get_cache_integration() -> CacheIntegration:
    """获取缓存集成单例"""
    global _cache_integration
    if _cache_integration is None:
        _cache_integration = CacheIntegration()
    return _cache_integration


# 便捷函数
def cache_get(key: str, category: str = "default") -> Any:
    """快速获取缓存"""
    return get_cache_integration().cache.get(key)


def cache_set(key: str, value: Any, category: str = "default", ttl: int = 60):
    """快速设置缓存"""
    get_cache_integration().cache.set(key, value, l2_ttl=ttl)


def cache_delete(key: str):
    """快速删除缓存"""
    get_cache_integration().cache.delete(key)