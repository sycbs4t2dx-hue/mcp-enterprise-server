"""
记忆管理核心服务
实现三级记忆存储、检索、更新、删除
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..common.config import get_settings
from ..common.logger import get_context_logger
from ..common.utils import generate_id, hash_content, utc_now
from ..models.tables import LongMemory
from .embedding_service import get_embedding_service
from .redis_client import get_redis_client
from .vector_db import get_vector_db_client

logger = get_context_logger(__name__)


class MemoryService:
    """记忆管理服务"""

    def __init__(self, db_session: Session):
        """
        初始化记忆服务

        Args:
            db_session: 数据库会话
        """
        self.db = db_session
        self.redis_client = get_redis_client()
        self.vector_db = get_vector_db_client()
        self.embedding_service = get_embedding_service()
        self.settings = get_settings()

        logger.info("记忆服务初始化完成")

    # ==================== 存储记忆 ====================

    def store_memory(
        self,
        project_id: str,
        content: str,
        memory_level: str = "mid",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        存储记忆

        Args:
            project_id: 项目ID
            content: 记忆内容
            memory_level: 记忆层级(short/mid/long)
            metadata: 元数据

        Returns:
            {memory_id, stored_at, memory_level}
        """
        start_time = time.time()

        # 生成记忆ID
        memory_id = generate_id("mem")
        timestamp = int(utc_now().timestamp())

        # 提取核心信息
        core_content = self._extract_core_info(content)

        # 计算相关性评分
        relevance_score = self._calculate_relevance_score(content, metadata or {})

        # 根据层级存储
        if memory_level == "short":
            success = self._store_short_memory(
                project_id, memory_id, core_content, relevance_score, metadata
            )

        elif memory_level == "mid":
            success = self._store_mid_memory(
                project_id, memory_id, core_content, timestamp, metadata
            )

        elif memory_level == "long":
            success = self._store_long_memory(
                project_id, memory_id, core_content, metadata
            )

        else:
            raise ValueError(f"无效的记忆层级: {memory_level}")

        elapsed = time.time() - start_time

        if success:
            logger.info(
                f"记忆存储成功",
                extra={
                    "memory_id": memory_id,
                    "project_id": project_id,
                    "level": memory_level,
                    "elapsed": f"{elapsed:.3f}s",
                },
            )

            return {
                "memory_id": memory_id,
                "stored_at": datetime.fromtimestamp(timestamp).isoformat(),
                "memory_level": memory_level,
            }
        else:
            raise RuntimeError("记忆存储失败")

    def _store_short_memory(
        self,
        project_id: str,
        memory_id: str,
        content: str,
        relevance_score: float,
        metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """存储短期记忆到Redis"""
        memory_data = {
            "memory_id": memory_id,
            "content": content,
            "timestamp": int(time.time()),
            "metadata": metadata or {},
        }

        ttl = self.settings.memory.short_term_ttl
        return self.redis_client.store_short_memory(
            project_id, memory_data, relevance_score, ttl
        )

    def _store_mid_memory(
        self,
        project_id: str,
        memory_id: str,
        content: str,
        timestamp: int,
        metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """存储中期记忆到Milvus"""
        try:
            # 生成嵌入
            embedding = self.embedding_service.encode_single(content, convert_to_numpy=False)

            # 准备数据
            data = [
                {
                    "memory_id": memory_id,
                    "project_id": project_id,
                    "embedding": embedding,
                    "content": content[:2000],  # Milvus字段长度限制
                    "category": (metadata or {}).get("category", "general"),
                    "created_at": timestamp,
                }
            ]

            # 插入向量数据库
            success, count = self.vector_db.insert_vectors("mid_term_memories", data)

            return success and count > 0

        except Exception as e:
            logger.error(f"中期记忆存储失败: {e}", extra={"memory_id": memory_id})
            return False

    def _store_long_memory(
        self,
        project_id: str,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """存储长期记忆到PostgreSQL"""
        try:
            metadata = metadata or {}

            long_mem = LongMemory(
                memory_id=memory_id,
                project_id=project_id,
                content=content,
                category=metadata.get("category", "general"),
                confidence=metadata.get("confidence", 0.80),
                metadata=metadata,
            )

            self.db.add(long_mem)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"长期记忆存储失败: {e}", extra={"memory_id": memory_id})
            return False

    # ==================== 检索记忆 ====================

    def retrieve_memory(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_levels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        检索记忆

        Args:
            project_id: 项目ID
            query: 查询内容
            top_k: 返回Top-K条
            memory_levels: 记忆层级列表,默认检索所有层级

        Returns:
            {memories: [...], total_token_saved: int}
        """
        start_time = time.time()

        # 检查缓存
        cached = self.redis_client.get_cached_retrieval(project_id, query)
        if cached:
            logger.debug("命中检索缓存", extra={"project_id": project_id})
            return cached

        # 默认检索所有层级
        if memory_levels is None:
            memory_levels = ["short", "mid", "long"]

        # 生成查询嵌入(用于向量检索)
        query_embedding = None
        if "mid" in memory_levels:
            query_embedding = self.embedding_service.encode_single(
                query, convert_to_numpy=False
            )

        # 并行检索三个层级
        all_memories = []

        if "short" in memory_levels:
            short_mems = self._retrieve_short_memories(project_id, top_k)
            all_memories.extend(short_mems)

        if "mid" in memory_levels and query_embedding:
            mid_mems = self._retrieve_mid_memories(
                project_id, query_embedding, top_k
            )
            all_memories.extend(mid_mems)

        if "long" in memory_levels:
            long_mems = self._retrieve_long_memories(project_id, query, top_k)
            all_memories.extend(long_mems)

        # 去重并排序
        unique_memories = self._deduplicate_memories(all_memories)
        sorted_memories = sorted(
            unique_memories, key=lambda x: x["relevance_score"], reverse=True
        )[:top_k]

        # 计算Token节省量(粗略估算)
        original_tokens = sum(len(m["content"]) // 4 for m in sorted_memories)
        compressed_tokens = original_tokens // 5  # 假设压缩率80%
        token_saved = original_tokens - compressed_tokens

        # 构建结果
        result = {
            "memories": sorted_memories,
            "total_token_saved": token_saved,
        }

        # 缓存结果
        cache_ttl = self.settings.memory.cache_ttl
        self.redis_client.cache_retrieval_result(project_id, query, result, cache_ttl)

        # 累计Token统计
        self.redis_client.increment_token_saved(project_id, token_saved)

        elapsed = time.time() - start_time
        logger.info(
            f"记忆检索完成",
            extra={
                "project_id": project_id,
                "count": len(sorted_memories),
                "token_saved": token_saved,
                "elapsed": f"{elapsed:.3f}s",
            },
        )

        return result

    def _retrieve_short_memories(
        self, project_id: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """检索短期记忆"""
        results = self.redis_client.get_short_memories(project_id, top_k)

        memories = []
        for memory_data, score in results:
            memories.append(
                {
                    "memory_id": memory_data.get("memory_id"),
                    "content": memory_data.get("content"),
                    "relevance_score": score,
                    "source": "short_term",
                    "timestamp": memory_data.get("timestamp"),
                    "metadata": memory_data.get("metadata"),
                }
            )

        return memories

    def _retrieve_mid_memories(
        self, project_id: str, query_embedding: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """检索中期记忆(向量检索)"""
        try:
            filter_expr = f'project_id == "{project_id}"'

            results = self.vector_db.search_vectors(
                collection_name="mid_term_memories",
                query_vectors=[query_embedding],
                top_k=top_k,
                filter_expr=filter_expr,
                output_fields=["memory_id", "content", "category", "created_at"],
            )

            memories = []
            if results and len(results) > 0:
                for hit in results[0]:
                    memories.append(
                        {
                            "memory_id": hit["entity"]["memory_id"],
                            "content": hit["entity"]["content"],
                            "relevance_score": hit["score"],
                            "source": "mid_term",
                            "category": hit["entity"]["category"],
                            "timestamp": hit["entity"]["created_at"],
                        }
                    )

            return memories

        except Exception as e:
            logger.error(f"中期记忆检索失败: {e}", extra={"project_id": project_id})
            return []

    def _retrieve_long_memories(
        self, project_id: str, query: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """检索长期记忆(SQL查询)"""
        try:
            # 提取查询关键词
            keywords = self._extract_keywords(query)

            # SQL查询(简化版:按置信度和类别匹配)
            long_mems = (
                self.db.query(LongMemory)
                .filter(LongMemory.project_id == project_id)
                .order_by(LongMemory.confidence.desc())
                .limit(top_k)
                .all()
            )

            memories = []
            for mem in long_mems:
                # 计算内容相似度(简单关键词匹配)
                content_lower = mem.content.lower()
                match_count = sum(1 for kw in keywords if kw in content_lower)
                relevance_score = min(match_count / max(len(keywords), 1), 1.0)

                memories.append(
                    {
                        "memory_id": mem.memory_id,
                        "content": mem.content,
                        "relevance_score": relevance_score * float(mem.confidence),
                        "source": "long_term",
                        "category": mem.category,
                        "confidence": float(mem.confidence),
                    }
                )

            return memories

        except Exception as e:
            logger.error(f"长期记忆检索失败: {e}", extra={"project_id": project_id})
            return []

    # ==================== 更新记忆 ====================

    def update_memory(
        self,
        memory_id: str,
        new_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_level: str = "long",
    ) -> bool:
        """
        更新记忆

        Args:
            memory_id: 记忆ID
            new_content: 新内容
            metadata: 新元数据
            memory_level: 记忆层级

        Returns:
            是否成功
        """
        try:
            if memory_level == "long":
                # 更新PostgreSQL
                mem = (
                    self.db.query(LongMemory)
                    .filter(LongMemory.memory_id == memory_id)
                    .first()
                )

                if mem:
                    mem.content = new_content
                    if metadata:
                        mem.metadata.update(metadata)
                    mem.updated_at = utc_now()

                    self.db.commit()

                    logger.info(f"记忆更新成功", extra={"memory_id": memory_id})
                    return True

                return False

            elif memory_level == "mid":
                # 向量数据库不支持原地更新,需删除后重新插入
                logger.warning("中期记忆更新需要删除后重新插入")
                return False

            else:
                logger.warning(f"暂不支持更新{memory_level}记忆")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"记忆更新失败: {e}", extra={"memory_id": memory_id})
            return False

    # ==================== 删除记忆 ====================

    def delete_memory(
        self, memory_id: str, project_id: str, memory_level: str = "long"
    ) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆ID
            project_id: 项目ID
            memory_level: 记忆层级

        Returns:
            是否成功
        """
        try:
            if memory_level == "short":
                return self.redis_client.delete_short_memory(project_id, memory_id)

            elif memory_level == "mid":
                expr = f'memory_id == "{memory_id}"'
                success, count = self.vector_db.delete_vectors("mid_term_memories", expr)
                return success and count > 0

            elif memory_level == "long":
                mem = (
                    self.db.query(LongMemory)
                    .filter(LongMemory.memory_id == memory_id)
                    .first()
                )

                if mem:
                    self.db.delete(mem)
                    self.db.commit()
                    logger.info(f"记忆删除成功", extra={"memory_id": memory_id})
                    return True

                return False

            else:
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"记忆删除失败: {e}", extra={"memory_id": memory_id})
            return False

    # ==================== 辅助方法 ====================

    def _extract_core_info(self, content: str) -> str:
        """提取核心信息(简化版)"""
        # 移除多余空白
        cleaned = re.sub(r"\s+", " ", content).strip()

        # 限制最大长度
        max_length = 2000
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length] + "..."

        return cleaned

    def _calculate_relevance_score(
        self, content: str, metadata: Dict[str, Any]
    ) -> float:
        """计算相关性评分"""
        # 简化实现:基于内容长度和置信度
        length_score = min(len(content) / 500, 1.0) * 0.6
        confidence = metadata.get("confidence", 0.5) * 0.4

        return length_score + confidence

    def _deduplicate_memories(
        self, memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """去重记忆(基于content hash)"""
        seen_hashes = set()
        unique = []

        for mem in memories:
            content_hash = hash_content(mem["content"], algorithm="md5")

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(mem)

        return unique

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词"""
        # 简单分词
        words = re.findall(r"\b\w{2,}\b", text.lower())

        # 停用词
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "的",
            "了",
            "在",
            "是",
        }

        # 过滤并去重
        keywords = [w for w in words if w not in stop_words]
        unique_keywords = list(dict.fromkeys(keywords))  # 保持顺序去重

        return unique_keywords[:max_keywords]
