"""
Vector Database Client Unit Tests
测试Milvus向量数据库客户端的所有功能
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pymilvus import DataType

from src.mcp_core.services.vector_db import VectorDBClient, get_vector_db_client


class TestVectorDBClientInit:
    """向量数据库客户端初始化测试"""

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.connections')
    @patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections')
    def test_init_success(self, mock_init_collections, mock_connections):
        """测试:初始化成功"""
        # Arrange
        mock_connections.connect.return_value = None
        
        # Act
        client = VectorDBClient(host="localhost", port=19530)
        
        # Assert
        mock_connections.connect.assert_called_once()
        mock_init_collections.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.connections')
    def test_init_connection_error(self, mock_connections):
        """测试:初始化失败 - 连接错误"""
        # Arrange
        mock_connections.connect.side_effect = Exception("Connection refused")
        
        # Act & Assert
        with pytest.raises(Exception, match="Connection refused"):
            VectorDBClient(host="invalid-host", port=19530)

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.connections')
    @patch('src.mcp_core.services.vector_db.utility')
    @patch('src.mcp_core.services.vector_db.VectorDBClient.create_collection')
    def test_init_collections_creates_missing(self, mock_create, mock_utility, mock_connections):
        """测试:初始化Collections - 创建缺失的"""
        # Arrange
        mock_connections.connect.return_value = None
        mock_utility.has_collection.return_value = False
        
        # Act
        client = VectorDBClient()
        
        # Assert - 应该为每个schema创建collection
        assert mock_create.call_count == len(VectorDBClient.COLLECTION_SCHEMAS)

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.connections')
    @patch('src.mcp_core.services.vector_db.utility')
    def test_init_collections_skips_existing(self, mock_utility, mock_connections):
        """测试:初始化Collections - 跳过已存在的"""
        # Arrange
        mock_connections.connect.return_value = None
        mock_utility.has_collection.return_value = True
        
        # Act
        client = VectorDBClient()
        
        # Assert - 不应该创建collection
        # (因为所有collection都已存在)


class TestCollectionManagement:
    """Collection管理测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    @patch('src.mcp_core.services.vector_db.CollectionSchema')
    @patch('src.mcp_core.services.vector_db.FieldSchema')
    def test_create_collection_success(self, mock_field, mock_schema, mock_collection, mock_vector_client):
        """测试:创建Collection成功"""
        # Arrange
        collection_name = "test_collection"
        schema_def = {
            "description": "Test collection",
            "fields": [
                {"name": "id", "dtype": DataType.VARCHAR, "max_length": 64, "is_primary": True},
                {"name": "embedding", "dtype": DataType.FLOAT_VECTOR, "dim": 768}
            ],
            "index": {
                "field_name": "embedding",
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16}
            }
        }
        
        mock_collection_instance = MagicMock()
        mock_collection.return_value = mock_collection_instance
        
        # Act
        result = mock_vector_client.create_collection(collection_name, schema_def)
        
        # Assert
        mock_collection.assert_called_once()
        mock_collection_instance.create_index.assert_called_once()
        mock_collection_instance.load.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.utility')
    def test_drop_collection_success(self, mock_utility, mock_vector_client):
        """测试:删除Collection成功"""
        # Arrange
        collection_name = "test_collection"
        mock_utility.has_collection.return_value = True
        mock_utility.drop_collection.return_value = None
        
        # Act
        result = mock_vector_client.drop_collection(collection_name)
        
        # Assert
        assert result is True
        mock_utility.drop_collection.assert_called_once_with(collection_name)

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.utility')
    def test_drop_collection_not_exists(self, mock_utility, mock_vector_client):
        """测试:删除Collection - 不存在"""
        # Arrange
        collection_name = "non_existent"
        mock_utility.has_collection.return_value = False
        
        # Act
        result = mock_vector_client.drop_collection(collection_name)
        
        # Assert
        assert result is False


class TestVectorOperations:
    """向量操作测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_insert_vectors_success(self, mock_collection_class, mock_vector_client):
        """测试:插入向量成功"""
        # Arrange
        collection_name = "mid_term_memories"
        data = [
            {
                "memory_id": "mem_001",
                "project_id": "proj_123",
                "embedding": [0.1] * 768,
                "content": "测试记忆",
                "category": "technical",
                "created_at": 1234567890
            }
        ]
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.insert.return_value = None
        mock_collection.flush.return_value = None
        
        # Act
        success, count = mock_vector_client.insert_vectors(collection_name, data)
        
        # Assert
        assert success is True
        assert count == 1
        mock_collection.insert.assert_called_once()
        mock_collection.flush.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_insert_vectors_batch(self, mock_collection_class, mock_vector_client):
        """测试:批量插入向量"""
        # Arrange
        collection_name = "mid_term_memories"
        # 创建150条数据测试批处理
        data = [
            {
                "memory_id": f"mem_{i:03d}",
                "project_id": "proj_123",
                "embedding": [0.1] * 768,
                "content": f"记忆{i}",
                "category": "technical",
                "created_at": 1234567890 + i
            }
            for i in range(150)
        ]
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        
        # Act
        success, count = mock_vector_client.insert_vectors(collection_name, data, batch_size=100)
        
        # Assert
        assert success is True
        assert count == 150
        # 应该调用2次insert (100 + 50)
        assert mock_collection.insert.call_count == 2

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_insert_vectors_error(self, mock_collection_class, mock_vector_client):
        """测试:插入向量失败"""
        # Arrange
        collection_name = "mid_term_memories"
        data = [{"memory_id": "mem_001"}]
        
        mock_collection_class.side_effect = Exception("Insert failed")
        
        # Act
        success, count = mock_vector_client.insert_vectors(collection_name, data)
        
        # Assert
        assert success is False
        assert count == 0

    @pytest.mark.unit
    def test_convert_to_entities(self, mock_vector_client):
        """测试:转换为列式数据"""
        # Arrange
        collection_name = "mid_term_memories"
        data = [
            {
                "memory_id": "mem_001",
                "project_id": "proj_123",
                "embedding": [0.1] * 768,
                "content": "记忆1",
                "category": "tech",
                "created_at": 100
            },
            {
                "memory_id": "mem_002",
                "project_id": "proj_123",
                "embedding": [0.2] * 768,
                "content": "记忆2",
                "category": "doc",
                "created_at": 200
            }
        ]
        
        # Act
        entities = mock_vector_client._convert_to_entities(data, collection_name)
        
        # Assert
        assert "memory_id" in entities
        assert "project_id" in entities
        assert len(entities["memory_id"]) == 2
        assert entities["memory_id"][0] == "mem_001"
        assert entities["memory_id"][1] == "mem_002"


class TestVectorSearch:
    """向量检索测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    @patch('src.mcp_core.services.vector_db.utility')
    def test_search_vectors_success(self, mock_utility, mock_collection_class, mock_vector_client):
        """测试:向量检索成功"""
        # Arrange
        collection_name = "mid_term_memories"
        query_vectors = [[0.1] * 768]
        
        # Mock检索结果
        mock_hit = MagicMock()
        mock_hit.id = "mem_001"
        mock_hit.distance = 0.15
        mock_hit.entity = MagicMock()
        mock_hit.entity.get = lambda field: {
            "memory_id": "mem_001",
            "content": "测试记忆",
            "category": "technical",
            "created_at": 1234567890
        }.get(field)
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.search.return_value = [[mock_hit]]
        
        mock_utility.load_state.return_value = MagicMock(name="Loaded")
        
        # Act
        results = mock_vector_client.search_vectors(collection_name, query_vectors, top_k=5)
        
        # Assert
        assert len(results) == 1
        assert len(results[0]) == 1
        assert results[0][0]["id"] == "mem_001"
        assert results[0][0]["distance"] == 0.15
        mock_collection.search.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    @patch('src.mcp_core.services.vector_db.utility')
    def test_search_vectors_with_filter(self, mock_utility, mock_collection_class, mock_vector_client):
        """测试:向量检索 - 带过滤条件"""
        # Arrange
        collection_name = "mid_term_memories"
        query_vectors = [[0.1] * 768]
        filter_expr = 'project_id == "proj_123"'
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.search.return_value = [[]]
        
        mock_utility.load_state.return_value = MagicMock(name="Loaded")
        
        # Act
        results = mock_vector_client.search_vectors(
            collection_name,
            query_vectors,
            top_k=5,
            filter_expr=filter_expr
        )
        
        # Assert
        # 验证过滤表达式被传递
        call_args = mock_collection.search.call_args
        assert call_args[1]["expr"] == filter_expr

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    @patch('src.mcp_core.services.vector_db.utility')
    def test_search_vectors_loads_collection(self, mock_utility, mock_collection_class, mock_vector_client):
        """测试:向量检索 - 自动加载Collection"""
        # Arrange
        collection_name = "mid_term_memories"
        query_vectors = [[0.1] * 768]
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.search.return_value = [[]]
        
        # Mock collection未加载
        mock_utility.load_state.return_value = MagicMock(name="NotLoaded")
        
        # Act
        results = mock_vector_client.search_vectors(collection_name, query_vectors)
        
        # Assert
        mock_collection.load.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_search_vectors_error(self, mock_collection_class, mock_vector_client):
        """测试:向量检索失败"""
        # Arrange
        collection_name = "mid_term_memories"
        query_vectors = [[0.1] * 768]
        
        mock_collection_class.side_effect = Exception("Search failed")
        
        # Act
        results = mock_vector_client.search_vectors(collection_name, query_vectors)
        
        # Assert
        assert results == []


class TestVectorDeletion:
    """向量删除测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_delete_vectors_success(self, mock_collection_class, mock_vector_client):
        """测试:删除向量成功"""
        # Arrange
        collection_name = "mid_term_memories"
        expr = 'memory_id in ["mem_001", "mem_002"]'
        
        mock_result = MagicMock()
        mock_result.delete_count = 2
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.delete.return_value = mock_result
        
        # Act
        success, count = mock_vector_client.delete_vectors(collection_name, expr)
        
        # Assert
        assert success is True
        assert count == 2
        mock_collection.delete.assert_called_once_with(expr)

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_delete_vectors_error(self, mock_collection_class, mock_vector_client):
        """测试:删除向量失败"""
        # Arrange
        collection_name = "mid_term_memories"
        expr = 'memory_id == "mem_001"'
        
        mock_collection_class.side_effect = Exception("Delete failed")
        
        # Act
        success, count = mock_vector_client.delete_vectors(collection_name, expr)
        
        # Assert
        assert success is False
        assert count == 0


class TestConditionalQuery:
    """条件查询测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_query_vectors_success(self, mock_collection_class, mock_vector_client):
        """测试:条件查询成功"""
        # Arrange
        collection_name = "mid_term_memories"
        expr = 'project_id == "proj_123"'
        
        mock_results = [
            {"memory_id": "mem_001", "content": "记忆1"},
            {"memory_id": "mem_002", "content": "记忆2"}
        ]
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.query.return_value = mock_results
        
        # Act
        results = mock_vector_client.query_vectors(collection_name, expr)
        
        # Assert
        assert len(results) == 2
        assert results[0]["memory_id"] == "mem_001"
        mock_collection.query.assert_called_once()

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_query_vectors_with_output_fields(self, mock_collection_class, mock_vector_client):
        """测试:条件查询 - 指定输出字段"""
        # Arrange
        collection_name = "mid_term_memories"
        expr = 'category == "technical"'
        output_fields = ["memory_id", "content"]
        
        mock_collection = MagicMock()
        mock_collection_class.return_value = mock_collection
        mock_collection.query.return_value = []
        
        # Act
        results = mock_vector_client.query_vectors(
            collection_name,
            expr,
            output_fields=output_fields
        )
        
        # Assert
        call_args = mock_collection.query.call_args
        assert call_args[1]["output_fields"] == output_fields

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_query_vectors_error(self, mock_collection_class, mock_vector_client):
        """测试:条件查询失败"""
        # Arrange
        collection_name = "mid_term_memories"
        expr = 'project_id == "proj_123"'
        
        mock_collection_class.side_effect = Exception("Query failed")
        
        # Act
        results = mock_vector_client.query_vectors(collection_name, expr)
        
        # Assert
        assert results == []


class TestCollectionStats:
    """Collection统计测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    @patch('src.mcp_core.services.vector_db.utility')
    def test_get_collection_stats_success(self, mock_utility, mock_collection_class, mock_vector_client):
        """测试:获取Collection统计成功"""
        # Arrange
        collection_name = "mid_term_memories"
        
        mock_collection = MagicMock()
        mock_collection.num_entities = 1000
        mock_collection_class.return_value = mock_collection
        
        mock_utility.load_state.return_value = MagicMock(name="Loaded")
        
        # Act
        stats = mock_vector_client.get_collection_stats(collection_name)
        
        # Assert
        assert stats["name"] == collection_name
        assert stats["num_entities"] == 1000
        assert stats["is_loaded"] is True

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.Collection')
    def test_get_collection_stats_error(self, mock_collection_class, mock_vector_client):
        """测试:获取统计失败"""
        # Arrange
        collection_name = "mid_term_memories"
        mock_collection_class.side_effect = Exception("Stats failed")
        
        # Act
        stats = mock_vector_client.get_collection_stats(collection_name)
        
        # Assert
        assert stats == {}


class TestConnectionManagement:
    """连接管理测试"""

    @pytest.fixture
    def mock_vector_client(self):
        """创建Mock向量数据库客户端"""
        with patch('src.mcp_core.services.vector_db.connections'):
            with patch('src.mcp_core.services.vector_db.VectorDBClient._init_collections'):
                client = VectorDBClient()
                yield client

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.connections')
    def test_close_connection(self, mock_connections, mock_vector_client):
        """测试:关闭连接"""
        # Act
        mock_vector_client.close()
        
        # Assert
        mock_connections.disconnect.assert_called_once_with("default")


class TestSingletonPattern:
    """单例模式测试"""

    @pytest.mark.unit
    @patch('src.mcp_core.services.vector_db.VectorDBClient')
    def test_get_vector_db_client_singleton(self, mock_client_class):
        """测试:单例模式"""
        # Arrange
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        
        # 重置单例
        import src.mcp_core.services.vector_db as vector_db_module
        vector_db_module._vector_db_client_instance = None
        
        # Act
        client1 = get_vector_db_client()
        client2 = get_vector_db_client()
        
        # Assert
        assert client1 is client2
        assert mock_client_class.call_count == 1
