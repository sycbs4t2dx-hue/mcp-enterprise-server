"""
Redis客户端封装
提供短期记忆存储、缓存管理、统计功能
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import redis
from redis.connection import ConnectionPool

from ..common.config import get_settings
from ..common.logger import get_logger
from ..common.utils import hash_content

logger = get_logger(__name__)


class RedisClient:
    """Redis客户端封装类"""

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化Redis客户端

        Args:
            redis_url: Redis连接URL,为None时使用配置文件
        """
        settings = get_settings()
        self.redis_url = redis_url or settings.redis.url

        # 创建连接池
        self.pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=settings.redis.max_connections,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
            decode_responses=False,  # 保持bytes,手动解码以支持复杂类型
        )

        # 创建客户端
        self.client = redis.Redis(connection_pool=self.pool)

        # 测试连接
        try:
            self.client.ping()
            logger.info("Redis连接成功", extra={"url": self._mask_url(self.redis_url)})
        except redis.ConnectionError as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    def _mask_url(self, url: str) -> str:
        """遮蔽URL中的密码"""
        import re

        return re.sub(r"(:\/\/[^:]+:)([^@]+)(@)", r"\1***\3", url)

    # ==================== 短期记忆操作 ====================

    def store_short_memory(
        self, project_id: str, memory_data: Dict[str, Any], relevance_score: float, ttl: int = 86400
    ) -> bool:
        """
        存储短期记忆(使用有序集合)

        Args:
            project_id: 项目ID
            memory_data: 记忆数据
            relevance_score: 相关性评分(0-1)
            ttl: 过期时间(秒),默认24小时

        Returns:
            是否存储成功
        """
        key = f"project:{project_id}:short_mem"

        try:
            # 序列化数据
            serialized_data = json.dumps(memory_data, ensure_ascii=False).encode("utf-8")

            # 使用Pipeline批量操作
            with self.client.pipeline() as pipe:
                # ZADD添加到有序集合(按relevance_score排序)
                pipe.zadd(key, {serialized_data: relevance_score})

                # 设置过期时间
                pipe.expire(key, ttl)

                # 限制集合大小(保留最高分的100条)
                pipe.zremrangebyrank(key, 0, -101)

                pipe.execute()

            logger.debug(
                f"短期记忆存储成功",
                extra={
                    "project_id": project_id,
                    "memory_id": memory_data.get("memory_id"),
                    "score": relevance_score,
                },
            )
            return True

        except Exception as e:
            logger.error(f"短期记忆存储失败: {e}", extra={"project_id": project_id})
            return False

    def get_short_memories(
        self, project_id: str, top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        检索短期记忆(按评分倒序)

        Args:
            project_id: 项目ID
            top_k: 返回Top-K条

        Returns:
            记忆列表[(memory_data, score), ...]
        """
        key = f"project:{project_id}:short_mem"

        try:
            # ZREVRANGE按分数倒序获取
            results = self.client.zrevrange(key, 0, top_k - 1, withscores=True)

            memories = []
            for data, score in results:
                try:
                    memory_data = json.loads(data.decode("utf-8"))
                    memories.append((memory_data, float(score)))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"反序列化记忆失败: {e}")
                    continue

            logger.debug(
                f"检索短期记忆",
                extra={"project_id": project_id, "count": len(memories), "top_k": top_k},
            )
            return memories

        except Exception as e:
            logger.error(f"检索短期记忆失败: {e}", extra={"project_id": project_id})
            return []

    def delete_short_memory(self, project_id: str, memory_id: str) -> bool:
        """
        删除指定短期记忆

        Args:
            project_id: 项目ID
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        key = f"project:{project_id}:short_mem"

        try:
            # 获取所有记忆,找到匹配的删除
            all_memories = self.client.zrange(key, 0, -1)

            for data in all_memories:
                try:
                    memory_data = json.loads(data.decode("utf-8"))
                    if memory_data.get("memory_id") == memory_id:
                        self.client.zrem(key, data)
                        logger.info(f"删除短期记忆", extra={"memory_id": memory_id})
                        return True
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            return False

        except Exception as e:
            logger.error(f"删除短期记忆失败: {e}", extra={"memory_id": memory_id})
            return False

    # ==================== 缓存操作 ====================

    def cache_retrieval_result(
        self, project_id: str, query: str, result: Dict[str, Any], ttl: int = 604800
    ) -> bool:
        """
        缓存检索结果

        Args:
            project_id: 项目ID
            query: 查询内容
            result: 检索结果
            ttl: 缓存过期时间(秒),默认7天

        Returns:
            是否缓存成功
        """
        # 生成缓存键(基于query内容hash)
        query_hash = hash_content(f"{project_id}:{query}", algorithm="md5")
        cache_key = f"cache:retrieve:{query_hash}"

        try:
            # 添加时间戳
            result["cached_at"] = int(__import__("time").time())

            # 序列化并设置过期
            serialized = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.client.setex(cache_key, ttl, serialized)

            logger.debug(f"缓存检索结果", extra={"query_hash": query_hash, "ttl": ttl})
            return True

        except Exception as e:
            logger.error(f"缓存检索结果失败: {e}")
            return False

    def get_cached_retrieval(self, project_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的检索结果

        Args:
            project_id: 项目ID
            query: 查询内容

        Returns:
            缓存的结果,不存在返回None
        """
        query_hash = hash_content(f"{project_id}:{query}", algorithm="md5")
        cache_key = f"cache:retrieve:{query_hash}"

        try:
            cached = self.client.get(cache_key)
            if cached:
                result = json.loads(cached.decode("utf-8"))
                logger.debug(f"命中缓存", extra={"query_hash": query_hash})
                return result

            return None

        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    def invalidate_cache(self, project_id: str, pattern: str = "*") -> int:
        """
        清除缓存

        Args:
            project_id: 项目ID
            pattern: 缓存键模式

        Returns:
            清除的缓存数量
        """
        cache_pattern = f"cache:retrieve:*{pattern}*"

        try:
            keys = self.client.keys(cache_pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"清除缓存", extra={"count": deleted, "pattern": pattern})
                return deleted

            return 0

        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0

    # ==================== 统计操作 ====================

    def increment_token_saved(self, project_id: str, tokens: int, date: Optional[str] = None) -> int:
        """
        累计Token节省量

        Args:
            project_id: 项目ID
            tokens: 节省的Token数
            date: 日期(YYYYMMDD),为None时使用今天

        Returns:
            累计Token数
        """
        if date is None:
            from datetime import datetime

            date = datetime.now().strftime("%Y%m%d")

        key = f"stats:token:{project_id}:{date}"

        try:
            total = self.client.incrby(key, tokens)
            # 设置过期时间(保留90天统计数据)
            self.client.expire(key, 7776000)

            return total

        except Exception as e:
            logger.error(f"累计Token统计失败: {e}")
            return 0

    def get_token_stats(self, project_id: str, days: int = 7) -> Dict[str, int]:
        """
        获取Token统计

        Args:
            project_id: 项目ID
            days: 统计天数

        Returns:
            {日期: Token数}
        """
        from datetime import datetime, timedelta

        stats = {}

        try:
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                key = f"stats:token:{project_id}:{date}"

                value = self.client.get(key)
                stats[date] = int(value) if value else 0

            return stats

        except Exception as e:
            logger.error(f"获取Token统计失败: {e}")
            return {}

    # ==================== 通用操作 ====================

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return bool(self.client.exists(key))

    def delete(self, *keys: str) -> int:
        """删除键"""
        if keys:
            return self.client.delete(*keys)
        return 0

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间(秒)"""
        return self.client.ttl(key)

    def close(self) -> None:
        """关闭连接"""
        self.client.close()
        logger.info("Redis连接已关闭")

    def __enter__(self) -> "RedisClient":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出"""
        self.close()


# 单例模式
_redis_client_instance: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    获取Redis客户端单例

    Returns:
        RedisClient实例
    """
    global _redis_client_instance

    if _redis_client_instance is None:
        _redis_client_instance = RedisClient()

    return _redis_client_instance
