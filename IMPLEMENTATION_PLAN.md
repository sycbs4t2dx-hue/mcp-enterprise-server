# MCP项目 - 剩余阶段实施方案

> **文档目的**: 详细规划Phase 3-9的实现步骤、代码结构、关键技术点

---

## 🎯 Phase 3: 记忆管理服务实现

### 3.1 Redis客户端封装

**文件**: `src/mcp_core/services/redis_client.py`

**核心功能**:
```python
class RedisClient:
    def __init__(self, config: RedisSettings):
        """初始化Redis连接池"""
        self.pool = redis.ConnectionPool.from_url(...)
        self.client = redis.Redis(connection_pool=self.pool)

    # 短期记忆操作
    def store_short_memory(self, project_id, memory_data, score):
        """ZADD存储,按relevance_score排序"""
        key = f"project:{project_id}:short_mem"
        self.client.zadd(key, {json.dumps(memory_data): score})
        self.client.expire(key, ttl)

    def get_short_memories(self, project_id, top_k):
        """ZREVRANGE检索Top-K"""
        return self.client.zrevrange(key, 0, top_k-1, withscores=True)

    # 缓存操作
    def cache_retrieval(self, cache_key, data, ttl):
        """SETEX缓存检索结果"""
        self.client.setex(cache_key, ttl, json.dumps(data))

    def get_cached(self, cache_key):
        """GET获取缓存"""
        return json.loads(self.client.get(cache_key) or "{}")
```

**技术要点**:
- 使用连接池避免频繁创建连接
- 有序集合(ZSET)实现按分数排序
- TTL自动过期(24小时)
- pipeline批量操作提升性能

---

### 3.2 Milvus向量数据库封装

**文件**: `src/mcp_core/services/vector_db.py`

**Collection Schema**:
```python
COLLECTION_SCHEMA = {
    "mid_term_memories": {
        "fields": [
            {"name": "memory_id", "type": "VarChar", "max_length": 64, "is_primary": True},
            {"name": "project_id", "type": "VarChar", "max_length": 64},
            {"name": "embedding", "type": "FloatVector", "dim": 768},
            {"name": "content", "type": "VarChar", "max_length": 2000},
            {"name": "category", "type": "VarChar", "max_length": 50},
            {"name": "created_at", "type": "Int64"},
        ],
        "index": {
            "field": "embedding",
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200}
        }
    }
}

class VectorDBClient:
    def create_collection(self, collection_name):
        """创建Collection(首次启动时)"""
        schema = CollectionSchema(fields=..., description=...)
        collection = Collection(name, schema)
        collection.create_index(...)

    def insert_vectors(self, collection_name, vectors_data):
        """批量插入向量"""
        collection.insert(vectors_data)
        collection.flush()  # 确保持久化

    def search_vectors(self, collection_name, query_vector, top_k, filter_expr):
        """向量检索"""
        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr  # 例如: f"project_id == '{project_id}'"
        )
        return results
```

**技术要点**:
- HNSW索引(高性能近似检索)
- COSINE余弦相似度
- 过滤表达式实现项目隔离
- 定期flush确保数据持久化

---

### 3.3 嵌入生成服务

**文件**: `src/mcp_core/services/embedding_service.py`

```python
from sentence_transformers import SentenceTransformer
import torch

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """初始化模型(单例)"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)
        self.dimension = self.model.get_sentence_embedding_dimension()  # 384

    def encode_single(self, text: str) -> List[float]:
        """生成单条嵌入"""
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量生成嵌入(性能优化)"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    @lru_cache(maxsize=1000)
    def encode_cached(self, text: str) -> tuple:
        """带缓存的嵌入生成(常用文本)"""
        return tuple(self.encode_single(text))
```

**性能优化**:
- GPU加速(如果可用)
- 批量处理减少模型调用
- LRU缓存常用文本(节省90%计算)

---

### 3.4 记忆管理核心服务

**文件**: `src/mcp_core/services/memory_service.py` (完整实现)

**类结构**:
```python
class MemoryService:
    def __init__(self):
        self.redis_client = RedisClient(...)
        self.vector_db = VectorDBClient(...)
        self.embedding_service = EmbeddingService(...)
        self.db_session = SessionLocal()

    # ========== 存储记忆 ==========
    def store_memory(self, project_id, content, memory_level, metadata):
        """
        核心逻辑:
        1. 提取核心信息(去除冗余)
        2. 计算相关性评分
        3. 根据层级存储:
           - short: Redis ZADD
           - mid: Milvus insert + embedding
           - long: PostgreSQL insert
        4. 返回memory_id
        """
        memory_id = generate_id("mem")

        if memory_level == "short":
            self.redis_client.store_short_memory(...)
        elif memory_level == "mid":
            embedding = self.embedding_service.encode_single(content)
            self.vector_db.insert_vectors(...)
        else:
            long_mem = LongMemory(...)
            self.db_session.add(long_mem)

        return {"memory_id": memory_id, "stored_at": ...}

    # ========== 检索记忆 ==========
    def retrieve_memory(self, project_id, query, top_k, memory_levels):
        """
        核心逻辑:
        1. 生成query嵌入
        2. 并行检索三个层级:
           - short: Redis ZREVRANGE
           - mid: Milvus search
           - long: PostgreSQL query
        3. 合并结果并去重
        4. 按relevance_score排序
        5. 返回Top-K + token节省量
        """
        # 检查缓存
        cache_key = f"retrieve:{hash(project_id + query)}"
        cached = self.redis_client.get_cached(cache_key)
        if cached:
            return cached

        # 生成嵌入
        query_embedding = self.embedding_service.encode_single(query)

        # 并行检索
        all_memories = []

        if "short" in memory_levels:
            short_mems = self.redis_client.get_short_memories(project_id, top_k)
            all_memories.extend(...)

        if "mid" in memory_levels:
            mid_results = self.vector_db.search_vectors(
                "mid_term_memories",
                query_embedding,
                top_k,
                filter_expr=f"project_id == '{project_id}'"
            )
            all_memories.extend(...)

        if "long" in memory_levels:
            long_mems = self.db_session.query(LongMemory).filter(...)
            all_memories.extend(...)

        # 去重+排序
        unique = self._deduplicate(all_memories)
        sorted_mems = sorted(unique, key=lambda x: x["relevance_score"], reverse=True)[:top_k]

        # 缓存结果
        result = {"memories": sorted_mems, "total_token_saved": ...}
        self.redis_client.cache_retrieval(cache_key, result, ttl=604800)

        return result

    # ========== 更新记忆 ==========
    def update_memory(self, memory_id, new_content, metadata):
        """
        冲突解决策略:
        1. 检查置信度(高覆盖低)
        2. 检查时间(新覆盖旧)
        3. 记录更新历史(audit_log)
        """
        pass

    # ========== 删除记忆 ==========
    def delete_memory(self, memory_id, memory_level):
        """软删除+审计日志"""
        pass

    # ========== 辅助方法 ==========
    def _deduplicate(self, memories):
        """基于content hash去重"""
        seen_hashes = set()
        unique = []
        for mem in memories:
            content_hash = hash_content(mem["content"])
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(mem)
        return unique
```

**关键技术点**:
1. **三级存储隔离**: Redis(热数据)/Milvus(语义检索)/PostgreSQL(核心事实)
2. **并行检索**: 三个数据源同时查询,最终合并
3. **智能缓存**: 检索结果缓存7天,相同query直接返回
4. **去重机制**: content hash + memory_id双重去重
5. **冲突解决**: 置信度优先,时间次优,人工兜底

---

## 🎯 Phase 4: Token优化服务实现

### 文件结构
```
src/mcp_core/services/
├── token_service.py         # 主服务
├── compressors/
│   ├── code_compressor.py   # 代码压缩(CodeBERT)
│   └── text_compressor.py   # 文本压缩(TextRank)
```

### 核心实现

**`token_service.py`**:
```python
class TokenOptimizationService:
    def compress_content(self, content, content_type, compression_ratio):
        """
        压缩流程:
        1. 检查缓存(hash(content))
        2. 判断内容类型
        3. 调用对应压缩器:
           - code: CodeBERT提取核心逻辑
           - text: TextRank摘要
        4. 计算Token节省量
        5. 缓存结果
        """
        # Token计算(粗略估算: 1 token ≈ 4字符)
        original_tokens = len(content) // 4

        if content_type == "code":
            compressed = self._compress_code(content, compression_ratio)
        else:
            compressed = self._compress_text(content, compression_ratio)

        compressed_tokens = len(compressed) // 4

        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_rate": 1 - (compressed_tokens / original_tokens),
            "compressed_content": compressed
        }

    def _compress_code(self, code, ratio):
        """
        代码压缩策略:
        1. AST解析提取函数签名
        2. 保留核心逻辑块
        3. 移除注释/空行
        4. CodeBERT语义压缩
        """
        import ast
        tree = ast.parse(code)

        # 提取函数定义
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        # 提取核心代码块(简化)
        core_code = "\n".join([ast.get_source_segment(code, func) for func in functions])

        return core_code[:int(len(core_code) * ratio)]
```

**`text_compressor.py`** (基于summa库):
```python
from summa.summarizer import summarize

def compress_text(text: str, ratio: float) -> str:
    """TextRank摘要"""
    try:
        return summarize(text, ratio=ratio)
    except:
        # 降级策略:简单截断
        return text[:int(len(text) * ratio)]
```

---

## 🎯 Phase 5: 幻觉抑制服务实现

### 文件: `src/mcp_core/services/hallucination_service.py`

```python
class HallucinationValidationService:
    def detect_hallucination(self, project_id, output, threshold):
        """
        检测流程:
        1. 生成output嵌入
        2. 检索相关记忆(Top-3)
        3. 计算余弦相似度
        4. 自适应调整阈值:
           - 长查询: -5%
           - 代码块: -8%
           - 技术术语密集: -5%
        5. 判断is_hallucination
        """
        output_embedding = self.embedding_service.encode_single(output)

        # 检索相关记忆
        memories = self.memory_service.retrieve_memory(
            project_id, output, top_k=3, memory_levels=["mid", "long"]
        )

        if not memories["memories"]:
            return {"is_hallucination": True, "confidence": 0.0, "reason": "无相关记忆"}

        # 计算相似度
        similarities = []
        for mem in memories["memories"]:
            mem_embedding = self.embedding_service.encode_single(mem["content"])
            sim = cosine_similarity(output_embedding, mem_embedding)
            similarities.append(sim)

        avg_similarity = np.mean(similarities)

        # 自适应阈值
        adjusted_threshold = self._calculate_adaptive_threshold(output, threshold)

        return {
            "is_hallucination": avg_similarity < adjusted_threshold,
            "confidence": avg_similarity,
            "matched_memories": [m["memory_id"] for m in memories["memories"]],
            "threshold_used": adjusted_threshold
        }

    def _calculate_adaptive_threshold(self, output, base_threshold):
        """
        自适应阈值算法(5个维度):
        1. 查询长度: >200字符 -> -0.05
        2. 代码块数量: >2个 -> -0.08
        3. 技术术语: ≥3个 -> -0.05
        4. 记忆数量: <10条 -> +0.05
        5. 用户历史幻觉率: >10% -> +0.10
        """
        adjustments = []

        if len(output) > 200:
            adjustments.append(-0.05)

        if output.count("```") > 2:
            adjustments.append(-0.08)

        tech_terms = ["API", "数据库", "框架", "接口"]
        if sum(1 for term in tech_terms if term in output) >= 3:
            adjustments.append(-0.05)

        final = base_threshold + sum(adjustments)
        return max(0.4, min(0.85, final))  # 限制[0.4, 0.85]
```

---

## 🎯 Phase 6: API层与权限系统实现

### 6.1 FastAPI主应用

**文件**: `src/mcp_core/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

app = FastAPI(
    title="MCP Core API",
    version="1.0.0",
    description="记忆控制机制REST API"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from .api.v1 import memory, token, hallucination, auth, project

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["记忆管理"])
app.include_router(token.router, prefix="/api/v1/token", tags=["Token优化"])
app.include_router(hallucination.router, prefix="/api/v1/validate", tags=["幻觉检测"])
app.include_router(project.router, prefix="/api/v1/project", tags=["项目管理"])

# Prometheus指标
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": utc_now().isoformat(),
        "version": "1.0.0"
    }
```

### 6.2 权限系统

**文件**: `src/mcp_core/api/dependencies/auth.py`

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """从JWT提取用户"""
    try:
        payload = jwt.decode(credentials.credentials, settings.security.jwt.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="无效Token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token验证失败")

def require_permission(permission: str):
    """权限检查装饰器"""
    async def check_perm(
        project_id: str,
        current_user: str = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # 查询权限
        perm = db.query(UserPermission).filter(
            UserPermission.user_id == current_user,
            UserPermission.project_id == project_id,
            UserPermission.permission == permission
        ).first()

        if not perm:
            raise HTTPException(status_code=403, detail=f"缺少权限: {permission}")

        # 检查过期
        if perm.expires_at and perm.expires_at < utc_now():
            raise HTTPException(status_code=403, detail="权限已过期")

        return current_user

    return check_perm
```

### 6.3 API路由示例

**文件**: `src/mcp_core/api/v1/memory.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/store", response_model=BaseResponse)
async def store_memory(
    request: MemoryStoreRequest,
    current_user: str = Depends(require_permission("memory:write")),
    db: Session = Depends(get_db)
):
    """存储记忆"""
    memory_service = MemoryService(db)
    result = memory_service.store_memory(
        project_id=request.project_id,
        content=request.content,
        memory_level=request.memory_level,
        metadata=request.metadata
    )

    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user,
        project_id=request.project_id,
        action="memory_store",
        resource_type="memory",
        resource_id=result["memory_id"]
    )
    db.add(audit_log)
    db.commit()

    return BaseResponse(data=result)

@router.get("/retrieve", response_model=BaseResponse)
async def retrieve_memory(
    project_id: str,
    query: str,
    top_k: int = 5,
    current_user: str = Depends(require_permission("memory:read")),
    db: Session = Depends(get_db)
):
    """检索记忆"""
    memory_service = MemoryService(db)
    result = memory_service.retrieve_memory(project_id, query, top_k)

    return BaseResponse(data=result)
```

---

## 🎯 Phase 7: 监控与日志系统实现

### 7.1 Prometheus指标

**文件**: `src/mcp_core/services/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# 业务指标
memory_operations = Counter(
    'mcp_memory_operations_total',
    'Total memory operations',
    ['operation', 'memory_level', 'project_id']
)

memory_retrieval_latency = Histogram(
    'mcp_memory_retrieval_latency_seconds',
    'Memory retrieval latency',
    ['project_id'],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
)

token_saved = Counter(
    'mcp_token_saved_total',
    'Total tokens saved',
    ['project_id', 'content_type']
)

# 使用示例
def track_memory_store(project_id, memory_level):
    memory_operations.labels(
        operation="store",
        memory_level=memory_level,
        project_id=project_id
    ).inc()
```

---

## 🎯 Phase 8-9: 测试与部署

### 8.1 单元测试示例

**文件**: `tests/unit/test_memory_service.py`

```python
import pytest
from src.mcp_core.services.memory_service import MemoryService

@pytest.fixture
def memory_service(db_session):
    return MemoryService(db_session)

def test_store_short_memory(memory_service):
    result = memory_service.store_memory(
        project_id="test_proj",
        content="测试内容",
        memory_level="short"
    )
    assert "memory_id" in result
    assert result["memory_id"].startswith("mem_")

def test_retrieve_memory_performance(memory_service):
    import time
    start = time.time()
    result = memory_service.retrieve_memory("test_proj", "测试查询", 5)
    elapsed = time.time() - start
    assert elapsed < 0.3  # 必须<300ms
```

### 8.2 Docker Compose

**文件**: `docker-compose.yml`

```yaml
version: '3.8'
services:
  mcp-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      - milvus

  postgres:
    image: postgres:15-alpine
    ...

  redis:
    image: redis:7-alpine
    ...

  milvus:
    image: milvusdb/milvus:v2.3.4
    ...
```

---

## ✅ 完成标准

每个Phase的验收清单:

**Phase 3**:
- [ ] Redis连接正常
- [ ] Milvus Collection创建成功
- [ ] 记忆存储/检索测试通过
- [ ] 性能测试:检索<300ms

**Phase 4**:
- [ ] Token压缩率≥80%
- [ ] 语义保留度测试通过

**Phase 5**:
- [ ] 幻觉检测准确率≥95%
- [ ] 边缘案例测试通过

**Phase 6**:
- [ ] 所有API端点测试通过
- [ ] 权限系统验证通过
- [ ] OpenAPI文档生成

**Phase 7**:
- [ ] Prometheus指标采集正常
- [ ] Grafana仪表盘配置完成

**Phase 8**:
- [ ] 测试覆盖率≥70%
- [ ] 性能压测100 QPS通过

**Phase 9**:
- [ ] Docker镜像构建成功
- [ ] 文档完整
- [ ] 部署文档验证

---

**预计总工时**: 24小时
**当前进度**: 6小时 (25%)
**下一里程碑**: Phase 3完成(预计+4小时)
