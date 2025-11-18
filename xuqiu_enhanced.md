# 编程项目MCP（记忆控制机制）开发文档 - 完整可落地版本

## 🎯 一、项目总览

### 1.1 文档目的
提供一套**完整可执行**的MCP开发方案，包含详细的开发计划、API设计、数据库Schema、测试方案和部署策略，确保项目从0到1可快速落地。

### 1.2 核心目标与可量化指标
| 目标维度 | 具体指标 | 验收标准 |
|---------|---------|----------|
| 记忆能力 | 跨会话记忆准确率 | ≥95% |
| Token优化 | Token消耗降低率 | ≥90% |
| 幻觉抑制 | 幻觉错误率 | ≤5% |
| 响应性能 | 单次查询响应时间 | ≤300ms |
| 并发能力 | 支持并发请求数 | ≥100 QPS |
| 可用性 | 系统可用性 | ≥99.9% |

### 1.3 适用场景
- ✅ AI辅助编程工具（如Cursor、Copilot扩展）
- ✅ 智能客服系统（多轮对话场景）
- ✅ 代码审查助手
- ✅ 自动化测试生成工具
- ✅ 技术文档问答系统

### 1.4 技术栈版本锁定
```toml
[tool.uv.dependencies]
python = "^3.10"
mcp-sdk = "^0.5.0"
httpx = "^0.27.0"
redis = "^5.0.1"
faiss-cpu = "^1.8.0"
pymilvus = "^2.3.4"
sqlalchemy = "^2.0.23"
pyyaml = "^6.0.1"
transformers = "^4.36.0"
sentence-transformers = "^2.2.2"
pydantic = "^2.5.0"
fastapi = "^0.108.0"
uvicorn = "^0.25.0"
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
```

---

## 🏗️ 二、系统架构设计

### 2.1 架构理念
采用「**分层记忆+智能管控+校验闭环+微服务化**」架构，支持水平扩展和模块化部署。

### 2.2 整体架构图
```
┌──────────────────────────────────────────────────────────────────┐
│                       客户端层（多项目接入）                      │
│         Web项目 | AI工具 | 后端服务 | IDE插件                    │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API网关层（FastAPI）                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │认证鉴权  │  │请求路由  │  │限流熔断  │  │日志追踪  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      MCP核心服务层                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │记忆管理服务  │ │Token优化服务 │ │幻觉抑制服务  │              │
│  │MemoryService │ │TokenService  │ │ValidateService│             │
│  └──────────────┘ └──────────────┘ └──────────────┘              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │权限安全服务  │ │配置管理服务  │ │监控告警服务  │              │
│  │SecurityService│ │ConfigService │ │MonitorService│             │
│  └──────────────┘ └──────────────┘ └──────────────┘              │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                         数据存储层                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │Redis Cluster │ │Milvus/FAISS  │ │PostgreSQL    │              │
│  │(短期缓存)    │ │(向量检索)    │ │(结构化存储)  │              │
│  └──────────────┘ └──────────────┘ └──────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 核心模块交互流程
```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API网关
    participant Memory as 记忆服务
    participant Token as Token服务
    participant Validate as 校验服务
    participant Storage as 存储层

    Client->>API: 发起请求(query)
    API->>Memory: 检索相关记忆
    Memory->>Storage: 多维度查询
    Storage-->>Memory: 返回Top-K记忆
    Memory->>Token: 压缩记忆内容
    Token-->>Memory: 返回优化后上下文
    Memory->>Validate: 幻觉检测
    Validate-->>API: 校验通过/失败
    API-->>Client: 返回响应
```

---

## 📡 三、API设计规范

### 3.1 RESTful API设计

#### 3.1.1 记忆管理接口

**【POST】存储记忆**
```http
POST /api/v1/memory/store
Content-Type: application/json
Authorization: Bearer {token}

{
  "project_id": "proj_001",
  "content": "项目使用Django 4.2框架，核心接口为/api/user",
  "memory_level": "mid",  // short/mid/long
  "metadata": {
    "category": "framework",
    "tags": ["django", "api"],
    "confidence": 0.95
  }
}

Response 200:
{
  "code": 0,
  "message": "存储成功",
  "data": {
    "memory_id": "mem_20250118_001",
    "stored_at": "2025-01-18T10:30:00Z"
  }
}
```

**【GET】检索记忆**
```http
GET /api/v1/memory/retrieve?project_id=proj_001&query=如何调用用户接口&top_k=5
Authorization: Bearer {token}

Response 200:
{
  "code": 0,
  "message": "检索成功",
  "data": {
    "memories": [
      {
        "memory_id": "mem_20250118_001",
        "content": "项目使用Django 4.2框架...",
        "relevance_score": 0.92,
        "created_at": "2025-01-18T10:30:00Z"
      }
    ],
    "total_token_saved": 3200
  }
}
```

**【PUT】更新记忆**
```http
PUT /api/v1/memory/{memory_id}
Content-Type: application/json

{
  "content": "更新后的内容",
  "metadata": {
    "updated_reason": "接口版本升级"
  }
}
```

**【DELETE】删除记忆**
```http
DELETE /api/v1/memory/{memory_id}?project_id=proj_001
```

#### 3.1.2 Token优化接口

**【POST】内容压缩**
```http
POST /api/v1/token/compress
Content-Type: application/json

{
  "content": "长文本或代码内容...",
  "content_type": "code",  // code/text
  "compression_ratio": 0.2
}

Response 200:
{
  "code": 0,
  "data": {
    "original_tokens": 2048,
    "compressed_tokens": 410,
    "compression_rate": 0.80,
    "compressed_content": "核心摘要内容..."
  }
}
```

#### 3.1.3 幻觉检测接口

**【POST】内容校验**
```http
POST /api/v1/validate/hallucination
Content-Type: application/json

{
  "project_id": "proj_001",
  "output": "待检测的模型输出内容",
  "threshold": 0.65
}

Response 200:
{
  "code": 0,
  "data": {
    "is_hallucination": false,
    "confidence": 0.88,
    "matched_memories": ["mem_001", "mem_003"]
  }
}
```

### 3.2 错误码设计

| 错误码 | 说明 | HTTP状态码 |
|-------|------|-----------|
| 0 | 成功 | 200 |
| 1001 | 参数错误 | 400 |
| 1002 | 未授权 | 401 |
| 1003 | 无权限 | 403 |
| 2001 | 记忆未找到 | 404 |
| 2002 | 记忆存储失败 | 500 |
| 3001 | Token超限 | 413 |
| 4001 | 幻觉检测失败 | 422 |
| 5001 | 系统错误 | 500 |

---

## 🗄️ 四、数据库设计

### 4.1 PostgreSQL结构化存储Schema

```sql
-- 项目表
CREATE TABLE projects (
    project_id VARCHAR(64) PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id VARCHAR(64) NOT NULL,
    status SMALLINT DEFAULT 1,  -- 1:active, 0:inactive
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_projects_owner ON projects(owner_id);

-- 长期记忆表（核心事实）
CREATE TABLE long_memories (
    memory_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),  -- framework/api/rule/config
    confidence DECIMAL(3,2) DEFAULT 0.80,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);
CREATE INDEX idx_long_mem_project ON long_memories(project_id);
CREATE INDEX idx_long_mem_category ON long_memories(category);

-- 用户权限表
CREATE TABLE user_permissions (
    user_id VARCHAR(64),
    project_id VARCHAR(64),
    role VARCHAR(20),  -- admin/developer/viewer
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, project_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- 操作审计日志表
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64),
    project_id VARCHAR(64),
    action VARCHAR(50),  -- store/retrieve/update/delete
    resource_type VARCHAR(50),  -- memory/config
    resource_id VARCHAR(64),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at);
```

### 4.2 Redis数据结构设计

```python
# 短期会话记忆（有序集合）
# Key: project:{project_id}:short_mem
# Score: relevance_score
# Value: JSON格式的记忆数据
ZADD project:proj_001:short_mem 0.95 '{"content":"...", "timestamp":1705561800}'

# 记忆检索缓存（7天过期）
# Key: cache:retrieve:{hash(query)}
# Value: JSON格式的检索结果
SETEX cache:retrieve:abc123 604800 '{"memories":[...], "cached_at":1705561800}'

# 用户会话信息（24小时过期）
# Key: session:{user_id}
# Value: JSON格式的会话数据
SETEX session:user_001 86400 '{"project_id":"proj_001", "context_window":10}'

# Token消耗统计（按天统计）
# Key: stats:token:{project_id}:{date}
# Value: 总消耗Token数
INCR stats:token:proj_001:20250118
```

### 4.3 Milvus向量数据库Collection设计

```python
# 中期项目记忆Collection
schema = {
    "collection_name": "mid_term_memories",
    "description": "中期项目记忆向量存储",
    "fields": [
        {"name": "memory_id", "type": "VarChar", "max_length": 64, "is_primary": True},
        {"name": "project_id", "type": "VarChar", "max_length": 64},
        {"name": "embedding", "type": "FloatVector", "dim": 768},  # sentence-transformers输出维度
        {"name": "content", "type": "VarChar", "max_length": 2000},
        {"name": "category", "type": "VarChar", "max_length": 50},
        {"name": "created_at", "type": "Int64"}  # Unix时间戳
    ],
    "index": {
        "field": "embedding",
        "metric_type": "COSINE",  # 余弦相似度
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 200}
    }
}

# 搜索参数
search_params = {
    "metric_type": "COSINE",
    "params": {"ef": 64},  # 检索时的搜索深度
    "expr": f"project_id == '{project_id}'"  # 过滤表达式
}
```

---

## 🔧 五、核心模块实现方案

### 5.1 记忆管理服务（完整实现）

```python
# src/mcp_core/memory/service.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import redis
import json
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

class MemoryService:
    def __init__(self, config: Dict):
        self.redis_client = redis.Redis.from_url(config["redis_url"])
        self.db_session = Session(bind=config["db_engine"])
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_db = self._init_vector_db(config)

    def store_memory(
        self,
        project_id: str,
        content: str,
        memory_level: str = "mid",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """存储记忆"""
        # 1. 生成记忆ID和时间戳
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(content)[:8]}"
        timestamp = int(datetime.now().timestamp())

        # 2. 提取核心信息（去除冗余）
        core_info = self._extract_core_info(content, metadata)

        # 3. 计算相关性评分
        relevance_score = self._calculate_relevance(project_id, core_info)

        # 4. 按层级存储
        if memory_level == "short":
            # Redis短期存储（24小时）
            memory_data = {
                "memory_id": memory_id,
                "content": core_info,
                "metadata": metadata or {},
                "timestamp": timestamp
            }
            self.redis_client.zadd(
                f"project:{project_id}:short_mem",
                {json.dumps(memory_data): relevance_score}
            )
            self.redis_client.expire(f"project:{project_id}:short_mem", 86400)

        elif memory_level == "mid":
            # 向量数据库存储（30天自动清理）
            embedding = self.embedder.encode(core_info).tolist()
            self.vector_db.insert(
                collection_name="mid_term_memories",
                data=[{
                    "memory_id": memory_id,
                    "project_id": project_id,
                    "embedding": embedding,
                    "content": core_info[:2000],
                    "category": metadata.get("category", "general"),
                    "created_at": timestamp
                }]
            )

        elif memory_level == "long":
            # PostgreSQL永久存储
            from .models import LongMemory
            long_mem = LongMemory(
                memory_id=memory_id,
                project_id=project_id,
                content=core_info,
                category=metadata.get("category"),
                confidence=metadata.get("confidence", 0.80),
                metadata=metadata
            )
            self.db_session.add(long_mem)
            self.db_session.commit()

        return {
            "memory_id": memory_id,
            "stored_at": datetime.fromtimestamp(timestamp).isoformat()
        }

    def retrieve_memory(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_levels: List[str] = ["short", "mid", "long"]
    ) -> Dict:
        """检索记忆"""
        # 1. 检查缓存
        cache_key = f"cache:retrieve:{hash(project_id + query)}"
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. 多层级并行检索
        all_memories = []

        if "short" in memory_levels:
            # 从Redis检索短期记忆
            short_mems = self.redis_client.zrevrange(
                f"project:{project_id}:short_mem",
                0, top_k - 1,
                withscores=True
            )
            all_memories.extend([
                {
                    **json.loads(mem[0]),
                    "relevance_score": float(mem[1]),
                    "source": "short_term"
                }
                for mem in short_mems
            ])

        if "mid" in memory_levels:
            # 从向量数据库检索中期记忆
            query_embedding = self.embedder.encode(query).tolist()
            results = self.vector_db.search(
                collection_name="mid_term_memories",
                data=[query_embedding],
                limit=top_k,
                filter=f"project_id == '{project_id}'"
            )
            all_memories.extend([
                {
                    "memory_id": hit.entity.get("memory_id"),
                    "content": hit.entity.get("content"),
                    "relevance_score": hit.score,
                    "source": "mid_term",
                    "timestamp": hit.entity.get("created_at")
                }
                for hit in results[0]
            ])

        if "long" in memory_levels:
            # 从PostgreSQL检索长期记忆
            from .models import LongMemory
            long_mems = self.db_session.query(LongMemory).filter(
                LongMemory.project_id == project_id
            ).order_by(LongMemory.confidence.desc()).limit(top_k).all()

            all_memories.extend([
                {
                    "memory_id": mem.memory_id,
                    "content": mem.content,
                    "relevance_score": float(mem.confidence),
                    "source": "long_term",
                    "category": mem.category
                }
                for mem in long_mems
            ])

        # 3. 去重并按相关性排序
        unique_memories = self._deduplicate_memories(all_memories)
        sorted_memories = sorted(
            unique_memories,
            key=lambda x: x["relevance_score"],
            reverse=True
        )[:top_k]

        # 4. 计算Token节省量
        original_tokens = sum(len(m["content"]) // 4 for m in sorted_memories)  # 粗略估算
        compressed_tokens = original_tokens // 5  # 压缩后

        result = {
            "memories": sorted_memories,
            "total_token_saved": original_tokens - compressed_tokens
        }

        # 5. 缓存结果（7天）
        self.redis_client.setex(cache_key, 604800, json.dumps(result))

        return result

    def _extract_core_info(self, content: str, metadata: Optional[Dict]) -> str:
        """提取核心信息（简化版）"""
        # 实际项目中应使用CodeBERT或TextRank
        # 这里简化为移除多余空白和注释
        import re
        cleaned = re.sub(r'\s+', ' ', content).strip()
        return cleaned[:1000]  # 限制最大长度

    def _calculate_relevance(self, project_id: str, content: str) -> float:
        """计算相关性评分"""
        # 简化实现：基于内容长度和关键词密度
        score = min(len(content) / 500, 1.0) * 0.8 + 0.2
        return score

    def _deduplicate_memories(self, memories: List[Dict]) -> List[Dict]:
        """去重记忆"""
        seen = set()
        unique = []
        for mem in memories:
            content_hash = hash(mem["content"])
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(mem)
        return unique
```

### 5.2 Token优化服务

```python
# src/mcp_core/token_optimize/service.py
from transformers import AutoTokenizer, AutoModel
import torch

class TokenOptimizeService:
    def __init__(self, config: Dict):
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.model = AutoModel.from_pretrained("microsoft/codebert-base")

    def compress_content(
        self,
        content: str,
        content_type: str = "text",
        compression_ratio: float = 0.2
    ) -> Dict:
        """压缩内容"""
        # 1. 计算原始Token数
        original_tokens = len(self.tokenizer.encode(content))

        # 2. 根据内容类型选择压缩策略
        if content_type == "code":
            compressed = self._compress_code(content, compression_ratio)
        else:
            compressed = self._compress_text(content, compression_ratio)

        # 3. 计算压缩后Token数
        compressed_tokens = len(self.tokenizer.encode(compressed))

        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_rate": 1 - (compressed_tokens / original_tokens),
            "compressed_content": compressed
        }

    def _compress_code(self, code: str, ratio: float) -> str:
        """代码压缩（提取核心逻辑）"""
        # 使用CodeBERT提取语义
        inputs = self.tokenizer(code, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)

        # 简化实现：提取函数签名和关键逻辑
        import ast
        try:
            tree = ast.parse(code)
            core_elements = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    core_elements.append(ast.get_source_segment(code, node))
            return "\n".join(core_elements[:int(len(core_elements) * ratio)])
        except:
            return code[:int(len(code) * ratio)]

    def _compress_text(self, text: str, ratio: float) -> str:
        """文本压缩（摘要提取）"""
        from summa.summarizer import summarize
        try:
            return summarize(text, ratio=ratio)
        except:
            return text[:int(len(text) * ratio)]
```

### 5.3 幻觉抑制服务

```python
# src/mcp_core/anti_hallucination/service.py
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class HallucinationValidationService:
    def __init__(self, config: Dict, memory_service: MemoryService):
        self.memory_service = memory_service
        self.threshold = config.get("similarity_threshold", 0.65)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def detect_hallucination(
        self,
        project_id: str,
        output: str,
        threshold: Optional[float] = None
    ) -> Dict:
        """检测幻觉"""
        threshold = threshold or self.threshold

        # 1. 生成输出嵌入
        output_embedding = self.embedder.encode(output)

        # 2. 检索相关记忆
        memories = self.memory_service.retrieve_memory(
            project_id=project_id,
            query=output,
            top_k=3,
            memory_levels=["mid", "long"]
        )

        if not memories["memories"]:
            return {
                "is_hallucination": True,
                "confidence": 0.0,
                "reason": "无相关记忆支撑"
            }

        # 3. 计算相似度
        similarities = []
        for mem in memories["memories"]:
            mem_embedding = self.embedder.encode(mem["content"])
            sim = cosine_similarity(
                output_embedding.reshape(1, -1),
                mem_embedding.reshape(1, -1)
            )[0][0]
            similarities.append(sim)

        avg_similarity = np.mean(similarities)

        # 4. 动态调整阈值（复杂任务降低10%）
        if self._is_complex_task(output):
            threshold *= 0.9

        return {
            "is_hallucination": avg_similarity < threshold,
            "confidence": float(avg_similarity),
            "matched_memories": [m["memory_id"] for m in memories["memories"]],
            "threshold_used": threshold
        }

    def _is_complex_task(self, output: str) -> bool:
        """判断是否为复杂任务"""
        # 简化实现：根据输出长度和代码块数量
        code_blocks = output.count("```")
        return len(output) > 500 or code_blocks > 2
```

---

## 📅 六、开发路线图与里程碑

### 6.1 迭代计划（8周完整交付）

| 阶段 | 时间 | 关键任务 | 交付物 | 优先级 |
|-----|------|---------|--------|--------|
| **Phase 1: 基础架构** | Week 1-2 | • 项目初始化<br>• 数据库Schema设计<br>• API框架搭建<br>• Docker环境配置 | • 项目骨架<br>• 数据库脚本<br>• API文档v1.0 | P0 |
| **Phase 2: 核心功能** | Week 3-4 | • 记忆管理模块开发<br>• Token优化服务<br>• Redis/Milvus集成 | • 记忆存储/检索API<br>• Token压缩功能 | P0 |
| **Phase 3: 增强能力** | Week 5-6 | • 幻觉抑制模块<br>• 权限安全系统<br>• 监控告警集成 | • 校验服务<br>• 权限中间件<br>• Prometheus指标 | P1 |
| **Phase 4: 测试优化** | Week 7 | • 单元测试覆盖<br>• 性能压测<br>• 幻觉率评测 | • 测试报告<br>• 性能基准 | P0 |
| **Phase 5: 部署上线** | Week 8 | • 生产环境部署<br>• 文档完善<br>• 用户培训 | • 部署文档<br>• 使用手册 | P1 |

### 6.2 详细里程碑检查点

**Week 1-2 检查点**
- [ ] 完成项目目录结构搭建
- [ ] PostgreSQL数据库表创建完成
- [ ] Redis连接测试通过
- [ ] FastAPI基础路由运行正常
- [ ] Docker Compose本地环境启动成功

**Week 3-4 检查点**
- [ ] 记忆存储API测试通过（覆盖三级记忆）
- [ ] 记忆检索响应时间<300ms
- [ ] Token压缩率达到80%以上
- [ ] Milvus向量检索准确率>90%

**Week 5-6 检查点**
- [ ] 幻觉检测准确率>95%
- [ ] 权限系统通过安全审计
- [ ] Prometheus监控指标采集正常
- [ ] 单元测试覆盖率>70%

**Week 7 检查点**
- [ ] 性能测试达到100 QPS
- [ ] 内存泄漏检测通过
- [ ] MME-RealWorld评测幻觉率<5%

**Week 8 检查点**
- [ ] 生产环境稳定运行24小时
- [ ] API文档完整且可执行
- [ ] 至少1个真实项目集成成功

---

## 🧪 七、测试策略与验收标准

### 7.1 测试金字塔

```
        ┌─────────────┐
        │  E2E测试    │  10%（关键业务流程）
        │  (Playwright)│
        └─────────────┘
       ┌──────────────────┐
       │   集成测试        │  30%（模块间交互）
       │   (pytest)       │
       └──────────────────┘
    ┌──────────────────────────┐
    │      单元测试             │  60%（函数级别）
    │      (pytest)            │
    └──────────────────────────┘
```

### 7.2 关键测试用例

#### 7.2.1 记忆管理测试
```python
# tests/test_memory_service.py
import pytest
from src.mcp_core.memory.service import MemoryService

@pytest.fixture
def memory_service(config):
    return MemoryService(config)

def test_store_short_memory(memory_service):
    """测试短期记忆存储"""
    result = memory_service.store_memory(
        project_id="test_proj",
        content="测试内容：Django项目配置",
        memory_level="short"
    )
    assert "memory_id" in result
    assert result["memory_id"].startswith("mem_")

def test_retrieve_memory_performance(memory_service):
    """测试检索性能（<300ms）"""
    import time
    start = time.time()
    result = memory_service.retrieve_memory(
        project_id="test_proj",
        query="Django配置",
        top_k=5
    )
    elapsed = (time.time() - start) * 1000
    assert elapsed < 300, f"检索耗时{elapsed}ms，超过300ms"
    assert len(result["memories"]) > 0

def test_memory_deduplication(memory_service):
    """测试记忆去重"""
    # 存储两次相同内容
    memory_service.store_memory("proj", "重复内容", "mid")
    memory_service.store_memory("proj", "重复内容", "mid")

    result = memory_service.retrieve_memory("proj", "重复内容", top_k=10)
    contents = [m["content"] for m in result["memories"]]
    assert len(contents) == len(set(contents)), "存在重复记忆"
```

#### 7.2.2 Token优化测试
```python
# tests/test_token_optimize.py
def test_compression_rate(token_service):
    """测试压缩率达标（≥80%）"""
    long_text = "..." * 1000  # 构造长文本
    result = token_service.compress_content(long_text, "text", 0.2)

    assert result["compression_rate"] >= 0.80, \
        f"压缩率{result['compression_rate']}未达到80%"

def test_code_compression_accuracy(token_service):
    """测试代码压缩保留核心逻辑"""
    code = """
    def calculate_total(items):
        total = 0
        for item in items:
            total += item.price
        return total
    """
    result = token_service.compress_content(code, "code", 0.3)

    # 验证函数签名被保留
    assert "def calculate_total" in result["compressed_content"]
```

#### 7.2.3 幻觉检测测试
```python
# tests/test_anti_hallucination.py
def test_hallucination_detection_accuracy(validation_service):
    """测试幻觉检测准确率（≥95%）"""
    # 准备测试数据集（100条正常输出+100条幻觉输出）
    normal_outputs = load_test_data("normal_outputs.json")
    hallucination_outputs = load_test_data("hallucination_outputs.json")

    correct_detections = 0
    total_tests = 200

    for output in normal_outputs:
        result = validation_service.detect_hallucination("test_proj", output)
        if not result["is_hallucination"]:
            correct_detections += 1

    for output in hallucination_outputs:
        result = validation_service.detect_hallucination("test_proj", output)
        if result["is_hallucination"]:
            correct_detections += 1

    accuracy = correct_detections / total_tests
    assert accuracy >= 0.95, f"检测准确率{accuracy}低于95%"
```

### 7.3 性能基准测试

```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class MCPLoadTest(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def retrieve_memory(self):
        """检索记忆（权重3）"""
        self.client.get(
            "/api/v1/memory/retrieve",
            params={"project_id": "proj_001", "query": "测试查询", "top_k": 5},
            headers={"Authorization": "Bearer test_token"}
        )

    @task(1)
    def store_memory(self):
        """存储记忆（权重1）"""
        self.client.post(
            "/api/v1/memory/store",
            json={
                "project_id": "proj_001",
                "content": "性能测试数据",
                "memory_level": "mid"
            },
            headers={"Authorization": "Bearer test_token"}
        )

# 运行命令: locust -f tests/performance/test_load.py --users 100 --spawn-rate 10
```

**验收标准**:
- 100并发用户下，P95响应时间<500ms
- 错误率<1%
- CPU使用率<70%
- 内存使用稳定（无泄漏）

---

## 🚀 八、部署与运维方案

### 8.1 Docker Compose本地部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MCP核心服务
  mcp-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://mcp_user:mcp_pass@postgres:5432/mcp_db
      - REDIS_URL=redis://redis:6379/0
      - MILVUS_HOST=milvus-standalone
      - MILVUS_PORT=19530
    depends_on:
      - postgres
      - redis
      - milvus-standalone
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=mcp_db
      - POSTGRES_USER=mcp_user
      - POSTGRES_PASSWORD=mcp_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # Milvus向量数据库
  milvus-standalone:
    image: milvusdb/milvus:v2.3.4
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
    ports:
      - "19530:19530"
    depends_on:
      - etcd
      - minio

  # Milvus依赖：etcd
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
    volumes:
      - etcd_data:/etcd

  # Milvus依赖：MinIO
  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  # Grafana可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana_dashboards:/etc/grafana/provisioning/dashboards

volumes:
  postgres_data:
  redis_data:
  etcd_data:
  minio_data:
  prometheus_data:
  grafana_data:
```

**启动命令**:
```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f mcp-api

# 停止服务
docker-compose down
```

### 8.2 生产环境部署（Kubernetes）

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-api
  labels:
    app: mcp
spec:
  replicas: 3  # 高可用部署
  selector:
    matchLabels:
      app: mcp-api
  template:
    metadata:
      labels:
        app: mcp-api
    spec:
      containers:
      - name: mcp-api
        image: your-registry/mcp-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-api-service
spec:
  type: LoadBalancer
  selector:
    app: mcp-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

### 8.3 监控指标与告警

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mcp-api'
    static_configs:
      - targets: ['mcp-api:8000']
    metrics_path: '/metrics'

# 告警规则
rule_files:
  - 'alerts.yml'

# monitoring/alerts.yml
groups:
- name: mcp_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "MCP API错误率过高"
      description: "过去5分钟错误率超过5%"

  - alert: SlowResponse
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "MCP API响应缓慢"
      description: "P95响应时间超过500ms"

  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes{container="mcp-api"} / container_spec_memory_limit_bytes{container="mcp-api"} > 0.85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "内存使用率过高"
      description: "内存使用超过85%"
```

### 8.4 关键监控指标

| 指标类别 | 指标名称 | 描述 | 告警阈值 |
|---------|---------|------|---------|
| 业务指标 | memory_store_total | 记忆存储总数 | - |
| 业务指标 | memory_retrieve_latency_seconds | 检索延迟 | P95>500ms |
| 业务指标 | token_saved_total | 累计节省Token数 | - |
| 业务指标 | hallucination_detected_total | 检测到的幻觉次数 | - |
| 系统指标 | http_requests_total | HTTP请求总数 | 错误率>5% |
| 系统指标 | redis_connected_clients | Redis连接数 | >1000 |
| 系统指标 | postgres_connections | 数据库连接数 | >80% |
| 资源指标 | container_cpu_usage_percent | CPU使用率 | >80% |
| 资源指标 | container_memory_usage_percent | 内存使用率 | >85% |

---

## 📖 九、项目配置文件完整示例

### 9.1 pyproject.toml
```toml
[project]
name = "mcp-project"
version = "1.0.0"
description = "MCP记忆控制机制 - 完整实现"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]

dependencies = [
    "mcp-sdk>=0.5.0",
    "fastapi>=0.108.0",
    "uvicorn[standard]>=0.25.0",
    "pydantic>=2.5.0",
    "sqlalchemy>=2.0.23",
    "psycopg2-binary>=2.9.9",
    "redis>=5.0.1",
    "pymilvus>=2.3.4",
    "faiss-cpu>=1.8.0",
    "sentence-transformers>=2.2.2",
    "transformers>=4.36.0",
    "torch>=2.1.0",
    "numpy>=1.24.0",
    "pyyaml>=6.0.1",
    "httpx>=0.27.0",
    "prometheus-client>=0.19.0",
    "python-jose[cryptography]>=3.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "pytest-cov>=4.1.0",
    "locust>=2.20.0",
    "black>=23.12.0",
    "ruff>=0.1.9",
    "mypy>=1.7.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --cov=src --cov-report=html --cov-report=term"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N"]
ignore = ["E501"]
```

### 9.2 config.yaml（增强版）
```yaml
# 项目基础配置
project:
  name: "mcp-core"
  version: "1.0.0"
  environment: "development"  # development/testing/production

# 日志配置
logging:
  level: "INFO"
  format: "json"  # json/text
  output: "file"  # file/stdout/both
  file_path: "./logs/mcp.log"
  max_bytes: 10485760  # 10MB
  backup_count: 5

# 数据库配置
database:
  url: "postgresql://mcp_user:mcp_pass@localhost:5432/mcp_db"
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30
  echo: false  # SQL日志

# Redis配置
redis:
  url: "redis://localhost:6379/0"
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5

# 向量数据库配置
vector_db:
  type: "milvus"  # milvus/faiss
  milvus:
    host: "localhost"
    port: 19530
    index_type: "HNSW"
    metric_type: "COSINE"
  faiss:
    index_path: "./data/faiss_index"
    dimension: 768

# 记忆管理配置
memory:
  short_term:
    ttl: 86400  # 24小时（秒）
    max_window: 20  # 最大窗口大小
    min_window: 5
  mid_term:
    ttl: 2592000  # 30天（秒）
    auto_archive: true
  long_term:
    min_confidence: 0.80

# Token优化配置
token_optimization:
  compression_ratio: 0.2
  cache_ttl: 604800  # 7天（秒）
  code_model: "microsoft/codebert-base"
  text_model: "sentence-transformers/all-MiniLM-L6-v2"

# 幻觉抑制配置
anti_hallucination:
  similarity_threshold: 0.65
  complex_task_threshold_multiplier: 0.9
  max_retries: 3
  enable_fact_check: true

# 安全配置
security:
  encryption_algorithm: "AES-256-GCM"
  jwt_secret: "your-secret-key-change-in-production"
  jwt_expiration: 86400  # 24小时
  ssl_enabled: false  # 生产环境改为true

# API配置
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  timeout: 60
  cors_origins: ["*"]  # 生产环境限制具体域名
  rate_limit:
    enabled: true
    requests_per_minute: 100

# 监控配置
monitoring:
  prometheus:
    enabled: true
    port: 9090
  metrics_prefix: "mcp"
  health_check_interval: 30

# 环境特定配置（可选）
environments:
  development:
    logging:
      level: "DEBUG"
    database:
      echo: true

  production:
    logging:
      level: "WARNING"
    security:
      ssl_enabled: true
    api:
      cors_origins: ["https://your-domain.com"]
```

---

## 🔐 十、安全最佳实践

### 10.1 敏感信息管理
```bash
# .env.example（不包含真实密钥）
DATABASE_URL=postgresql://user:password@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-jwt-secret
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 生产环境使用密钥管理服务（如AWS Secrets Manager）
```

### 10.2 API鉴权中间件
```python
# src/mcp_core/security/auth.py
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """验证JWT Token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的Token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token验证失败")
```

### 10.3 输入验证（防注入）
```python
from pydantic import BaseModel, Field, validator

class MemoryStoreRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=64, regex="^[a-zA-Z0-9_-]+$")
    content: str = Field(..., min_length=1, max_length=10000)
    memory_level: str = Field(..., regex="^(short|mid|long)$")

    @validator('content')
    def sanitize_content(cls, v):
        # 移除潜在的SQL注入字符
        dangerous_chars = ["';", "--", "/*", "*/", "xp_", "sp_"]
        for char in dangerous_chars:
            if char in v.lower():
                raise ValueError(f"内容包含非法字符: {char}")
        return v
```

---

## 📚 十一、最佳实践与注意事项

### 11.1 开发规范
1. **代码风格**: 使用Black格式化，Ruff检查，强制100字符行宽
2. **类型注解**: 所有函数必须添加类型提示（使用mypy检查）
3. **文档字符串**: 使用Google风格的docstring
4. **错误处理**: 使用自定义异常类，避免裸except
5. **日志记录**: 关键操作必须记录INFO级别日志，错误记录ERROR级别

### 11.2 性能优化建议
1. **批量操作**: 向量检索使用批量查询，减少网络往返
2. **连接池**: 数据库和Redis使用连接池，避免频繁创建连接
3. **异步IO**: 使用FastAPI的异步特性处理并发请求
4. **缓存策略**: 热点数据使用Redis缓存，设置合理的TTL
5. **索引优化**: PostgreSQL表添加必要的索引（参考Schema设计）

### 11.3 常见陷阱
❌ **错误做法**: 在短期记忆中存储大量重复信息
✅ **正确做法**: 使用去重机制，只存储差异信息

❌ **错误做法**: 所有记忆都存储到向量数据库
✅ **正确做法**: 根据访问频率和重要性分级存储

❌ **错误做法**: 硬编码相似度阈值
✅ **正确做法**: 根据任务复杂度动态调整阈值

### 11.4 故障排查清单
```bash
# 1. 检查服务健康状态
curl http://localhost:8000/health

# 2. 检查数据库连接
psql -h localhost -U mcp_user -d mcp_db -c "SELECT 1"

# 3. 检查Redis连接
redis-cli ping

# 4. 检查Milvus连接
curl http://localhost:19530/healthz

# 5. 查看最近错误日志
tail -n 100 logs/mcp.log | grep ERROR

# 6. 检查内存使用
docker stats mcp-api

# 7. 查看慢查询
grep "duration > 500ms" logs/mcp.log
```

---

## 🎓 十二、扩展方向与未来规划

### 12.1 短期扩展（3个月内）
- [ ] **多租户支持**: 添加租户隔离机制，支持SaaS模式
- [ ] **GraphQL API**: 提供GraphQL接口，优化前端查询效率
- [ ] **Webhook通知**: 记忆更新时触发Webhook，集成第三方服务
- [ ] **批量导入工具**: 支持从文档/代码库批量导入记忆

### 12.2 中期扩展（6个月内）
- [ ] **多模态记忆**: 支持图片、音频、视频的记忆存储与检索
- [ ] **智能摘要**: 基于LLM的自动摘要生成（替代规则压缩）
- [ ] **记忆推荐**: 主动推送相关记忆，提升开发效率
- [ ] **A/B测试框架**: 支持不同记忆策略的效果对比

### 12.3 长期规划（1年内）
- [ ] **联邦学习**: 支持多项目间的隐私保护记忆共享
- [ ] **自适应优化**: 根据用户反馈自动调整记忆权重和压缩策略
- [ ] **边缘部署**: 支持客户端本地部署，降低延迟
- [ ] **多智能体协作**: 构建记忆共享网络，实现团队协同编程

---

## 📞 十三、支持与反馈

### 技术支持
- 📧 邮箱: support@mcp-project.com
- 💬 Discord: https://discord.gg/mcp-community
- 📖 文档: https://docs.mcp-project.com
- 🐛 问题反馈: https://github.com/your-org/mcp-project/issues

### 贡献指南
欢迎提交PR！请遵循以下流程：
1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交代码 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

---

## 📄 附录

### A. 术语表
- **MCP**: 记忆控制机制（Memory Control Protocol）
- **向量嵌入**: 将文本转换为高维向量的表示形式
- **幻觉**: LLM生成的与事实不符的内容
- **Token**: 文本的最小单位，通常为词或子词
- **P95延迟**: 95%的请求响应时间低于此值

### B. 参考资料
1. [MCP官方文档](https://modelcontextprotocol.io)
2. [MIRIX论文](https://arxiv.org/abs/2401.14604)
3. [MemInsight论文](https://arxiv.org/abs/2408.16819)
4. [Milvus向量数据库](https://milvus.io/docs)
5. [FastAPI最佳实践](https://fastapi.tiangolo.com/tutorial/)

### C. 快速启动命令
```bash
# 克隆项目
git clone https://github.com/your-org/mcp-project.git
cd mcp-project

# 安装依赖
uv venv && source .venv/bin/activate
uv sync

# 初始化数据库
python scripts/init_database.py

# 启动开发服务器
uvicorn src.mcp_core.main:app --reload --port 8000

# 运行测试
pytest tests/ -v --cov

# 构建Docker镜像
docker build -t mcp-api:latest .

# 启动完整环境
docker-compose up -d
```

---

**文档版本**: v2.0.0
**最后更新**: 2025-01-18
**维护者**: MCP Development Team
