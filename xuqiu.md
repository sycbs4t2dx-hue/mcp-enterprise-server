
# 编程项目MCP（记忆控制机制）开发文档
## 一、文档概述
### 1. 文档目的
提供一套可落地的MCP开发方案，实现编程项目的**记忆增强、Token优化、幻觉抑制**三大核心目标，明确从架构设计到部署上线的全流程规范，适配各类编程项目（Web/AI/后端等）的集成需求。

### 2. 核心目标
- 记忆能力：支持短期会话上下文保留与长期核心信息持久化，实现跨会话记忆复用
- Token优化：通过结构化存储、摘要压缩等手段，降低Token消耗90%以上（参考mem0实践数据）
- 幻觉抑制：建立三级校验机制，将幻觉率控制在5%以内，保障输出准确性
- 扩展性：模块化设计，支持多项目集成、多模态信息（文本/代码/配置）存储

### 3. 适用范围
适用于需要集成LLM能力的编程项目，包括但不限于AI辅助开发工具、智能客服系统、自动化编程平台等，支持Python/Java/Go等主流开发语言。

## 二、总体架构设计
### 1. 架构理念
采用「**分层记忆+智能管控+校验闭环**」架构，参考MIRIX多模态记忆系统与MemInsight结构化增强思想，平衡记忆完整性、Token效率与准确性。

### 2. 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│ 应用层（编程项目）                                          │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP核心层                                                   │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│ │ 记忆管理模块  │ │ Token优化模块 │ │ 幻觉抑制模块  │       │
│ └───────────────┘ └───────────────┘ └───────────────┘       │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│ │ 权限安全模块  │ │ 配置管理模块  │ │ 日志监控模块  │       │
│ └───────────────┘ └───────────────┘ └───────────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 存储层                                                       │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│ │ 短期缓存（Redis）│ │ 向量数据库    │ │ 结构化存储（SQL）│       │
│ └───────────────┘ └───────────────┘ └───────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 3. 技术选型
| 模块         | 推荐技术栈                                  | 选型依据                                                                 |
|--------------|---------------------------------------------|--------------------------------------------------------------------------|
| 核心开发语言 | Python 3.10+                                | 适配MCP SDK，生态丰富，支持主流向量库与LLM API                           |
| 短期缓存     | Redis                                       | 高性能，支持滑动窗口数据快速读写，适配会话级记忆                          |
| 向量数据库   | 小型项目：FAISS；中大型项目：Milvus         | 平衡检索速度与扩展性，支持语义相似性计算                                 |
| 结构化存储   | SQLite（本地）/MySQL（分布式）              | 存储核心事实、权限配置等结构化数据，保障数据一致性                       |
| 摘要算法     | TextRank（通用）+ CodeBERT（代码场景）      | 精准提取代码/文本核心信息，压缩率达80%以上                               |
| 加密方案     | AES-256-GCM                                 | 满足敏感信息加密需求，适配MCP通信安全标准                                 |
| 测试工具     | pytest + MME-RealWorld评测集                | 覆盖功能、性能、幻觉率全维度测试                                          |

## 三、核心模块详细设计
### 1. 记忆管理模块（核心）
#### 1.1 记忆分层设计
参考MIRIX六种记忆类型，结合编程项目特性优化为三级记忆结构：
- 短期会话记忆（1-24小时）：存储最近5-20轮关键交互（动态窗口），含临时变量、未确认结论
  - 实现：Redis有序集合，按时间戳+相关性排序，自动淘汰低价值信息
  - 窗口调整策略：根据Token消耗动态扩容（最高不超过4096 Token），复杂任务窗口扩大30%
- 中期项目记忆（7-30天）：存储项目核心规则、接口定义、历史结论，支持增量更新
- 长期基础记忆（永久）：存储通用编程知识、语法规则、权限配置，仅手动更新

#### 1.2 记忆操作流程
1. 写入：原始信息 → 上下文分析器（相关性评估+冗余检测）→ 结构化提取（实体/规则/步骤）→ 按层级存储
2. 检索：当前需求 → 多维度匹配（语义相似性+时间关联性）→ Top-K相关记忆 → 去重整合
3. 更新：新信息与存量记忆对比 → 冲突自动校验（高置信度覆盖低置信度）→ 增量写入
4. 淘汰：短期记忆按LRU淘汰，中期记忆按访问频率（30天无访问自动归档）

#### 1.3 核心代码示例（记忆存储）
```python
def store_memory(memory_data: dict, memory_level: str = "short"):
    """
    记忆存储核心函数
    :param memory_data: 记忆数据（含content、timestamp、relevance_score等）
    :param memory_level: 记忆层级（short/mid/long）
    """
    from src.build_mcp.common.config import load_config
    config = load_config()
    
    # 结构化提取核心信息（参考MemInsight属性挖掘）
    core_info = extract_structured_info(memory_data["content"])
    memory_data["core_info"] = core_info
    
    # 按层级存储
    if memory_level == "short":
        # Redis短期存储，设置24小时过期
        redis_client.zadd(
            f"project:{memory_data['project_id']}:short_mem",
            {json.dumps(memory_data): memory_data["relevance_score"]},
            nx=True
        )
        redis_client.expire(f"project:{memory_data['project_id']}:short_mem", 86400)
    elif memory_level == "mid":
        # 向量数据库存储，用于语义检索
        embedding = generate_embedding(core_info)
        vector_db.insert(
            collection_name=f"project_{memory_data['project_id']}_mid",
            data={"id": uuid.uuid4().hex, "embedding": embedding, "metadata": memory_data}
        )
```

### 2. Token优化模块
#### 2.1 核心优化策略
- 结构化存储：仅存储「不可再生信息」（项目规则、接口定义、独有逻辑），通用编程知识复用长期基础记忆
- 摘要压缩：长文本（代码/文档）通过CodeBERT提取核心逻辑，1000字→200字摘要（压缩率80%）
- 缓存复用：相同需求的记忆检索结果缓存7天，重复请求直接复用，避免重复计算
- 增量更新：仅追加新信息，不重复存储已确认的核心事实（参考mem0去重机制）

#### 2.2 Token消耗控制目标
| 场景                | 优化前Token消耗 | 优化后Token消耗 | 优化率 |
|---------------------|-----------------|-----------------|--------|
| 单轮简单查询        | 512-1024        | 64-128          | 87.5%  |
| 多轮复杂编程任务    | 4096-8192       | 256-512         | 93.75% |
| 跨会话项目复用      | 8192-16384      | 512-1024        | 93.75% |

#### 2.3 关键实现代码（摘要压缩）
```python
def compress_content(content: str, content_type: str = "code") -> str:
    """
    内容压缩函数，减少Token消耗
    :param content: 原始内容（代码/文本）
    :param content_type: 内容类型（code/text）
    :return: 压缩后的核心摘要
    """
    if len(content) < 200:
        return content  # 短内容无需压缩
    
    if content_type == "code":
        # 代码场景：提取语法树核心逻辑
        from transformers import CodeBERTTokenizer, CodeBERTModel
        tokenizer = CodeBERTTokenizer.from_pretrained("mrm8488/codebert-base-finetuned-stackoverflow-qa")
        inputs = tokenizer(content, return_tensors="pt", truncation=True, max_length=512)
        outputs = CodeBERTModel.from_pretrained("mrm8488/codebert-base-finetuned-stackoverflow-qa")(**inputs)
        core_logic = extract_code_core(outputs.last_hidden_state)
        return core_logic[:300]  # 限制最大长度
    else:
        # 文本场景：TextRank摘要
        from summa.summarization import summarize
        return summarize(content, ratio=0.2)  # 提取20%核心内容
```

### 3. 幻觉抑制模块
#### 3.1 三级校验机制
- 事前校验：记忆检索时，通过余弦相似度（阈值≥0.65）过滤不相关记忆，避免噪声干扰
- 事中检测：生成响应时，实时计算输出内容与长期知识库的嵌入相似度，低于阈值则触发追问
- 事后过滤：基于MME-RealWorld基准，对输出内容进行事实核查，过滤虚构信息

#### 3.2 核心校验代码示例
```python
def detect_hallucination(output: str, project_id: str, threshold: float = 0.65) -> bool:
    """
    幻觉检测函数
    :param output: 模型生成输出
    :param project_id: 项目ID
    :param threshold: 相似度阈值
    :return: True=存在幻觉，False=正常
    """
    # 生成输出内容嵌入
    output_embedding = generate_embedding(output)
    
    # 检索项目长期知识库
    collection = vector_db.get_collection(f"project_{project_id}_long")
    results = collection.query(
        query_embeddings=[output_embedding],
        n_results=3,
        include_metadata=True
    )
    
    # 计算相似度
    similarities = [float(cos_sim(output_embedding, res)) for res in results["embeddings"][0]]
    avg_similarity = sum(similarities) / len(similarities)
    
    # 动态调整阈值（复杂任务阈值降低10%）
    if is_complex_task(output):
        threshold *= 0.9
    
    return avg_similarity < threshold
```

#### 3.3 冲突解决策略
当新信息与存量记忆冲突时，按以下优先级处理：
1. 置信度优先：高置信度信息（如官方文档、用户确认结论）覆盖低置信度信息
2. 时间优先：同置信度下，新信息替换旧信息
3. 人工介入：冲突无法自动解决时，触发用户确认流程，记录最终结论

### 4. 权限安全模块
#### 4.1 权限控制设计
遵循最小权限原则，实现细粒度访问控制：
- 项目级隔离：不同项目记忆库独立存储，禁止跨项目访问
- 角色权限：管理员（全权限）、开发者（读写权限）、访客（只读权限）
- 动态授权：工具调用时根据任务类型临时授权，任务结束后回收权限

#### 4.2 安全防护措施
- 通信加密：采用SSL/TLS传输加密，消息体通过AES-256-GCM加密（参考MCP安全规范）
- 隐私保护：敏感信息（API密钥、密码）脱敏存储，禁止记忆库存储原始敏感数据
- 日志审计：记录所有记忆操作（写入/检索/更新），支持追溯审计

## 四、项目目录结构
采用PyPA推荐的`src/`布局，降低打包错误率63%，确保多环境一致性：
```
mcp-project/
├── src/                          # 核心源码目录
│   └── mcp_core/                 # 主包命名空间
│       ├── __init__.py           # 包初始化
│       ├── memory/               # 记忆管理模块
│       │   ├── __init__.py
│       │   ├── storage.py        # 记忆存储逻辑
│       │   └── retrieval.py      # 记忆检索逻辑
│       ├── token_optimize/       # Token优化模块
│       │   ├── __init__.py
│       │   └── compression.py    # 摘要压缩逻辑
│       ├── anti_hallucination/   # 幻觉抑制模块
│       │   ├── __init__.py
│       │   └── validation.py     # 校验逻辑
│       ├── security/             # 权限安全模块
│       │   ├── __init__.py
│       │   └── auth.py           # 权限控制
│       └── common/               # 通用功能模块
│           ├── config.py         # 配置管理
│           ├── logger.py         # 日志记录
│           └── utils.py          # 工具函数
├── tests/                        # 测试套件目录
│   ├── test_memory.py
│   ├── test_token_optimize.py
│   └── test_anti_hallucination.py
├── pyproject.toml                # 项目构建配置
├── config.yaml                   # 配置文件
└── Makefile                      # 自动化命令管理
```

## 五、部署与集成指南
### 1. 环境配置
#### 1.1 系统要求
- 操作系统：Windows 10+/Linux/Unix
- Python版本：3.10+
- 依赖管理：UV（推荐）或pip

#### 1.2 环境搭建步骤
```bash
# 安装UV（Windows PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 创建项目目录并初始化
uv init mcp-project && cd mcp-project
uv venv && source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装依赖
uv add mcp-sdk httpx pytest redis faiss-cpu pyyaml transformers
```

### 2. 配置文件示例（config.yaml）
```yaml
# 基础配置
project_name: "code_assistant_mcp"
log_level: "INFO"
log_dir: "./logs"

# 记忆配置
short_memory_window: 10  # 短期记忆默认窗口大小（轮次）
mid_memory_ttl: 2592000  # 中期记忆过期时间（30天，秒）
vector_db_type: "faiss"  # 向量数据库类型（faiss/milvus）

# Token优化配置
compression_ratio: 0.2  # 文本压缩比例
cache_ttl: 604800       # 缓存过期时间（7天，秒）

# 幻觉抑制配置
similarity_threshold: 0.65  # 相似度阈值
max_retries: 3              # 接口重试次数

# 安全配置
encryption_algorithm: "AES-256-GCM"
ssl_enabled: True
```

### 3. 项目集成示例（Python项目）
```python
# 1. 初始化MCP
from src.mcp_core import MCP

mcp = MCP(config_path="config.yaml")

# 2. 写入项目记忆
project_memory = {
    "project_id": "web_project_001",
    "content": "项目采用Django 4.2框架，数据库使用MySQL，核心接口：/api/user（GET/POST）",
    "memory_level": "mid",
    "relevance_score": 0.9
}
mcp.memory_store.store_memory(project_memory)

# 3. 检索记忆并生成响应
user_query = "如何调用项目的用户接口？"
relevant_memories = mcp.memory_retrieval.retrieve_memory(
    query=user_query,
    project_id="web_project_001"
)

# 4. 优化Token并生成输出
optimized_context = mcp.token_compress.compress_content(str(relevant_memories))
output = mcp.generate_response(user_query, optimized_context)

# 5. 幻觉检测
if mcp.anti_hallucination.detect_hallucination(output, "web_project_001"):
    output = "需要进一步确认项目接口细节，请提供更多信息"

print(output)
```

### 4. 部署方式
- 本地部署：直接运行源码，适用于小型项目或开发测试
- Docker部署：打包为容器镜像，支持跨环境部署
- 分布式部署：中大型项目可将存储层（向量数据库/Redis）独立部署，提高并发能力

## 六、测试与优化指南
### 1. 测试用例设计
#### 1.1 功能测试
- 记忆测试：验证三级记忆的写入、检索、更新、淘汰功能
- Token测试：统计优化前后的Token消耗，确保达标
- 幻觉测试：使用MME-RealWorld评测集，验证幻觉率≤5%

#### 1.2 性能测试
- 响应时间：单轮检索响应≤300ms，生成响应≤1s
- 并发能力：支持100+并发请求，无内存泄漏

### 2. 优化建议
- 记忆优化：根据项目类型调整记忆窗口大小（代码项目窗口可缩小20%）
- Token优化：高频复用的代码片段可预压缩存储，进一步降低消耗
- 幻觉优化：针对特定领域（如医疗/金融）提高相似度阈值至0.75以上

## 七、最佳实践与注意事项
1. 避免硬编码敏感信息，使用环境变量或安全存储服务
2. 定期清理过期记忆，避免存储冗余导致检索效率下降
3. 复杂项目建议按模块拆分记忆库（如接口记忆、规则记忆、历史结论记忆）
4. 集成时优先复用长期基础记忆，减少重复存储通用知识
5. 日志记录需包含记忆操作详情，便于问题排查与审计

## 八、扩展方向
1. 多模态支持：扩展图片、音频等多模态信息的记忆存储与校验
2. 多智能体协作：支持多智能体共享记忆库，实现协同编程
3. 自学习优化：基于用户反馈自动调整记忆权重与压缩比例
4. 跨平台同步：支持不同编程工具（IDE/编辑器）间的记忆同步

需要我针对你的具体编程项目类型（如Python Web/AI开发工具/后端服务），定制模块适配代码和集成方案吗？可以直接对接现有项目结构，省去适配成本。
