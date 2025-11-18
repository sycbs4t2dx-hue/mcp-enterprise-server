"""
Milvus向量数据库客户端封装
提供Collection管理、向量插入/检索、索引优化
"""

from typing import Any, Dict, List, Optional, Tuple

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from ..common.config import get_settings
from ..common.logger import get_logger

logger = get_logger(__name__)


class VectorDBClient:
    """Milvus向量数据库客户端"""

    # Collection Schema定义
    COLLECTION_SCHEMAS = {
        "mid_term_memories": {
            "description": "中期项目记忆向量存储",
            "fields": [
                {"name": "memory_id", "dtype": DataType.VARCHAR, "max_length": 64, "is_primary": True},
                {"name": "project_id", "dtype": DataType.VARCHAR, "max_length": 64},
                {"name": "embedding", "dtype": DataType.FLOAT_VECTOR, "dim": 768},
                {"name": "content", "dtype": DataType.VARCHAR, "max_length": 2000},
                {"name": "category", "dtype": DataType.VARCHAR, "max_length": 50},
                {"name": "created_at", "dtype": DataType.INT64},
            ],
            "index": {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        }
    }

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        初始化Milvus客户端

        Args:
            host: Milvus服务地址
            port: Milvus服务端口
        """
        settings = get_settings()
        self.host = host or settings.vector_db.milvus.host
        self.port = port or settings.vector_db.milvus.port
        self.index_type = settings.vector_db.milvus.index_type
        self.metric_type = settings.vector_db.milvus.metric_type

        # 连接Milvus
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                timeout=settings.vector_db.milvus.timeout,
            )
            logger.info(f"Milvus连接成功", extra={"host": self.host, "port": self.port})
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            raise

        # 初始化Collections
        self._init_collections()

    def _init_collections(self) -> None:
        """初始化所有Collection(如果不存在则创建)"""
        for collection_name, schema_def in self.COLLECTION_SCHEMAS.items():
            if not utility.has_collection(collection_name):
                self.create_collection(collection_name, schema_def)
                logger.info(f"创建Collection: {collection_name}")
            else:
                logger.debug(f"Collection已存在: {collection_name}")

    def create_collection(self, collection_name: str, schema_def: Dict[str, Any]) -> Collection:
        """
        创建Collection

        Args:
            collection_name: Collection名称
            schema_def: Schema定义

        Returns:
            Collection对象
        """
        try:
            # 构建字段
            fields = []
            for field_def in schema_def["fields"]:
                if field_def["dtype"] == DataType.FLOAT_VECTOR:
                    field = FieldSchema(
                        name=field_def["name"],
                        dtype=field_def["dtype"],
                        dim=field_def["dim"],
                    )
                elif field_def["dtype"] == DataType.VARCHAR:
                    field = FieldSchema(
                        name=field_def["name"],
                        dtype=field_def["dtype"],
                        max_length=field_def["max_length"],
                        is_primary=field_def.get("is_primary", False),
                    )
                else:
                    field = FieldSchema(
                        name=field_def["name"],
                        dtype=field_def["dtype"],
                        is_primary=field_def.get("is_primary", False),
                    )
                fields.append(field)

            # 创建Schema
            schema = CollectionSchema(
                fields=fields,
                description=schema_def.get("description", ""),
            )

            # 创建Collection
            collection = Collection(name=collection_name, schema=schema)

            # 创建索引
            if "index" in schema_def:
                index_params = schema_def["index"]
                collection.create_index(
                    field_name=index_params["field_name"],
                    index_params={
                        "index_type": index_params["index_type"],
                        "metric_type": index_params["metric_type"],
                        "params": index_params["params"],
                    },
                )

            # 加载到内存
            collection.load()

            logger.info(
                f"Collection创建成功",
                extra={
                    "name": collection_name,
                    "fields": len(fields),
                    "index": schema_def.get("index", {}).get("index_type"),
                },
            )

            return collection

        except Exception as e:
            logger.error(f"创建Collection失败: {e}", extra={"name": collection_name})
            raise

    def insert_vectors(
        self,
        collection_name: str,
        data: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> Tuple[bool, int]:
        """
        批量插入向量

        Args:
            collection_name: Collection名称
            data: 数据列表,每项包含所有字段
            batch_size: 批处理大小

        Returns:
            (是否成功, 插入数量)
        """
        try:
            collection = Collection(collection_name)

            # 转换为列式数据(Milvus要求)
            entities = self._convert_to_entities(data, collection_name)

            # 批量插入
            total_inserted = 0
            for i in range(0, len(data), batch_size):
                batch_entities = {key: values[i : i + batch_size] for key, values in entities.items()}

                collection.insert(batch_entities)
                total_inserted += min(batch_size, len(data) - i)

            # Flush确保持久化
            collection.flush()

            logger.info(
                f"向量插入成功",
                extra={"collection": collection_name, "count": total_inserted},
            )

            return True, total_inserted

        except Exception as e:
            logger.error(
                f"向量插入失败: {e}",
                extra={"collection": collection_name, "data_size": len(data)},
            )
            return False, 0

    def _convert_to_entities(
        self, data: List[Dict[str, Any]], collection_name: str
    ) -> Dict[str, List[Any]]:
        """
        转换为列式数据格式

        Args:
            data: 行式数据
            collection_name: Collection名称

        Returns:
            列式数据 {field_name: [values]}
        """
        schema_def = self.COLLECTION_SCHEMAS[collection_name]
        field_names = [field["name"] for field in schema_def["fields"]]

        entities = {field: [] for field in field_names}

        for item in data:
            for field in field_names:
                entities[field].append(item.get(field))

        return entities

    def search_vectors(
        self,
        collection_name: str,
        query_vectors: List[List[float]],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
        output_fields: Optional[List[str]] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        向量检索

        Args:
            collection_name: Collection名称
            query_vectors: 查询向量列表
            top_k: 返回Top-K结果
            filter_expr: 过滤表达式,例如 'project_id == "proj_001"'
            output_fields: 返回字段列表

        Returns:
            检索结果 [[{id, distance, entity}, ...], ...]
        """
        try:
            collection = Collection(collection_name)

            # 确保Collection已加载
            if not utility.load_state(collection_name).name == "Loaded":
                collection.load()

            # 获取配置
            settings = get_settings()
            search_params = {
                "metric_type": self.metric_type,
                "params": settings.vector_db.milvus.search_params,
            }

            # 默认输出字段
            if output_fields is None:
                output_fields = ["memory_id", "content", "category", "created_at"]

            # 执行搜索
            results = collection.search(
                data=query_vectors,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=output_fields,
            )

            # 格式化结果
            formatted_results = []
            for hits in results:
                hit_list = []
                for hit in hits:
                    hit_dict = {
                        "id": hit.id,
                        "distance": float(hit.distance),
                        "score": float(hit.score) if hasattr(hit, "score") else 1 - float(hit.distance),
                        "entity": {field: hit.entity.get(field) for field in output_fields},
                    }
                    hit_list.append(hit_dict)
                formatted_results.append(hit_list)

            logger.debug(
                f"向量检索完成",
                extra={
                    "collection": collection_name,
                    "query_count": len(query_vectors),
                    "top_k": top_k,
                },
            )

            return formatted_results

        except Exception as e:
            logger.error(
                f"向量检索失败: {e}",
                extra={"collection": collection_name, "filter": filter_expr},
            )
            return []

    def delete_vectors(
        self, collection_name: str, expr: str
    ) -> Tuple[bool, int]:
        """
        删除向量

        Args:
            collection_name: Collection名称
            expr: 删除表达式,例如 'memory_id in ["mem_001", "mem_002"]'

        Returns:
            (是否成功, 删除数量)
        """
        try:
            collection = Collection(collection_name)

            # 执行删除
            result = collection.delete(expr)

            logger.info(
                f"向量删除成功",
                extra={"collection": collection_name, "expr": expr, "count": result.delete_count},
            )

            return True, result.delete_count

        except Exception as e:
            logger.error(f"向量删除失败: {e}", extra={"collection": collection_name, "expr": expr})
            return False, 0

    def query_vectors(
        self,
        collection_name: str,
        expr: str,
        output_fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        条件查询(非向量检索)

        Args:
            collection_name: Collection名称
            expr: 查询表达式
            output_fields: 输出字段
            limit: 返回数量限制

        Returns:
            查询结果列表
        """
        try:
            collection = Collection(collection_name)

            results = collection.query(
                expr=expr,
                output_fields=output_fields or ["*"],
                limit=limit,
            )

            logger.debug(
                f"条件查询完成",
                extra={"collection": collection_name, "count": len(results)},
            )

            return results

        except Exception as e:
            logger.error(f"条件查询失败: {e}", extra={"collection": collection_name, "expr": expr})
            return []

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取Collection统计信息

        Args:
            collection_name: Collection名称

        Returns:
            统计信息
        """
        try:
            collection = Collection(collection_name)

            stats = {
                "name": collection_name,
                "num_entities": collection.num_entities,
                "is_loaded": utility.load_state(collection_name).name == "Loaded",
            }

            logger.debug(f"获取Collection统计", extra=stats)

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def drop_collection(self, collection_name: str) -> bool:
        """
        删除Collection(危险操作!)

        Args:
            collection_name: Collection名称

        Returns:
            是否成功
        """
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.warning(f"Collection已删除: {collection_name}")
                return True

            return False

        except Exception as e:
            logger.error(f"删除Collection失败: {e}")
            return False

    def close(self) -> None:
        """关闭连接"""
        connections.disconnect("default")
        logger.info("Milvus连接已关闭")


# 单例模式
_vector_db_client_instance: Optional[VectorDBClient] = None


def get_vector_db_client() -> VectorDBClient:
    """
    获取向量数据库客户端单例

    Returns:
        VectorDBClient实例
    """
    global _vector_db_client_instance

    if _vector_db_client_instance is None:
        _vector_db_client_instance = VectorDBClient()

    return _vector_db_client_instance
