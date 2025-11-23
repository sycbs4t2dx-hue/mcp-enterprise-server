# 混合记忆存储系统集成文档

> 日期: 2025-11-21
> 版本: v1.0.0
> 状态: 完成

## 概述

混合记忆存储系统 (Hybrid Memory Storage System) 将本地高性能存储 (SQLite) 与团队共享存储 (MySQL) 无缝结合，并与项目记忆系统 (Project Memory System) 深度集成，提供智能的项目记忆管理能力。

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Tools Layer                             │
│   (memory_mcp_tools.py - 10 个工具)                              │
├─────────────────────────────────────────────────────────────────┤
│                 Integrated Memory Manager                         │
│   (memory_hybrid_integration.py)                                 │
├────────────────────────┬────────────────────────────────────────┤
│   Hybrid Storage       │        Project Memory System            │
│   (hybrid_storage.py)  │        (project_memory_system.py)       │
├────────────┬───────────┼────────────────────────────────────────┤
│   Local    │  Central  │     Graph Generator                     │
│  (SQLite)  │  (MySQL)  │     (project_graph_generator.py)        │
└────────────┴───────────┴────────────────────────────────────────┘
```

## 核心组件

### 1. HybridStorageManager (混合存储管理器)

**文件**: `src/mcp_core/services/hybrid_storage_system.py`

**功能**:
- 本地SQLite存储: 毫秒级响应，离线可用
- 中央MySQL存储: 团队共享，永久保存
- 智能同步策略: 自动/手动/按重要性同步
- 多级缓存: 内存缓存减少数据库访问

**主要方法**:
```python
class HybridStorageManager:
    async def save(data, options) -> str             # 智能保存
    async def load(snapshot_id) -> Dict              # 多级加载
    async def search(query, options) -> List[Dict]   # 并行搜索
    async def sync_to_central() -> int               # 同步到中央
    async def share_insight(content, tags)           # 分享洞察
    async def analyze_patterns() -> Dict             # 分析模式
    def get_stats() -> Dict                          # 获取统计
```

### 2. IntegratedMemoryManager (集成记忆管理器)

**文件**: `src/mcp_core/services/memory_hybrid_integration.py`

**功能**:
- 结合HybridStorage和ProjectMemory的优势
- 统一的记忆管理接口
- 增强的搜索和恢复能力
- 综合统计和分析

**主要方法**:
```python
class IntegratedMemoryManager:
    async def create_snapshot(trigger, context, sync_options) -> Dict
    async def search_memories(query, search_options) -> List[Dict]
    async def recover_memory(query_type, parameters) -> MemoryRecoveryResult
    async def sync_to_team() -> Dict
    async def share_insight(content, tags) -> Dict
    async def get_team_insights(limit) -> List[Dict]
    async def analyze_patterns() -> Dict
    async def get_file_history(file_path) -> Dict
    def get_statistics() -> Dict
    async def cleanup(days) -> Dict
```

### 3. MCP Tools (MCP工具层)

**文件**: `src/mcp_core/memory_mcp_tools.py`

**提供10个MCP工具**:

| 工具名 | 功能描述 |
|--------|----------|
| `create_memory_snapshot` | 创建项目记忆快照 |
| `search_memories` | 多源并行搜索记忆 |
| `recover_memory_by_similarity` | 基于相似度恢复记忆 |
| `get_file_memory_history` | 获取文件历史 |
| `sync_memories_to_team` | 同步到团队存储 |
| `share_insight` | 分享洞察到团队 |
| `get_team_insights` | 获取团队洞察 |
| `analyze_memory_patterns` | 分析记忆模式 |
| `get_memory_statistics` | 获取统计信息 |
| `cleanup_old_memories` | 清理旧记忆 |

## 数据流

### 快照创建流程

```
1. 用户触发 create_memory_snapshot
         ↓
2. IntegratedMemoryManager.create_snapshot()
         ↓
3. ProjectMemorySystem 生成图谱快照
         ↓
4. 转换为存储格式
         ↓
5. HybridStorageManager.save()
         ├─→ LocalSQLiteStorage.save() [同步]
         └─→ CentralMySQLStorage.save() [异步, 可选]
         ↓
6. 返回快照ID和洞察
```

### 搜索流程

```
1. 用户触发 search_memories(query)
         ↓
2. HybridStorageManager.search()
         ├─→ 检查缓存
         ├─→ _search_local() [本地SQLite]
         ├─→ _search_central() [中央MySQL]
         └─→ _search_team_projects() [团队项目]
         ↓
3. 并行执行，收集结果
         ↓
4. 去重、排序、增强结果
         ↓
5. 返回搜索结果列表
```

## 存储结构

### 本地SQLite存储

位置: `{project_path}/.mcp_memory/local.db`

```sql
CREATE TABLE snapshots (
    id TEXT PRIMARY KEY,
    timestamp REAL,
    data TEXT,        -- JSON格式的快照数据
    metadata TEXT,    -- JSON格式的元数据
    hash TEXT,        -- 数据哈希
    synced INTEGER,   -- 是否已同步
    sync_time REAL    -- 同步时间
);
```

### 中央MySQL存储

```sql
CREATE TABLE memory_snapshots (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50),
    project_path TEXT,
    timestamp DATETIME,
    trigger_type VARCHAR(50),
    node_count INTEGER,
    edge_count INTEGER,
    complexity FLOAT,
    graph_data TEXT,      -- JSON格式
    metadata TEXT,        -- JSON格式
    insights TEXT,        -- JSON格式
    hash VARCHAR(100),
    created_by VARCHAR(100),
    team_id VARCHAR(50),
    is_public BOOLEAN
);

CREATE TABLE shared_insights (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    project_id VARCHAR(50),
    insight_type VARCHAR(50),
    content TEXT,
    created_at DATETIME,
    created_by VARCHAR(100),
    upvotes INTEGER,
    tags TEXT             -- JSON数组
);

CREATE TABLE memory_patterns (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    pattern_type VARCHAR(50),
    pattern_data TEXT,
    frequency INTEGER,
    projects TEXT,        -- JSON数组
    first_seen DATETIME,
    last_seen DATETIME,
    confidence FLOAT
);
```

## 配置说明

### 环境变量

```bash
# 团队模式
MCP_TEAM_MODE=true         # 启用团队模式
MCP_TEAM_ID=team_001       # 团队ID

# 数据库配置 (在 config.py 中)
DB_HOST=localhost
DB_PORT=3306
DB_USER=mcp_user
DB_PASSWORD=your_password
DB_NAME=mcp_memory
```

### 存储模式

```python
# 自动模式 (根据MCP_TEAM_MODE决定)
manager = create_storage(project_path, mode='auto')

# 纯本地模式 (只使用SQLite)
manager = create_storage(project_path, mode='local')

# 混合模式 (SQLite + MySQL)
manager = create_storage(project_path, mode='hybrid')

# 纯中央模式 (主要使用MySQL)
manager = create_storage(project_path, mode='central')
```

## 使用示例

### 基础使用

```python
from src.mcp_core.services import create_integrated_manager

# 创建管理器
manager = create_integrated_manager(
    project_path="/path/to/project",
    storage_mode='hybrid'
)

# 创建快照
result = await manager.create_snapshot(
    trigger='manual',
    context={'reason': '功能完成'},
    sync_options={'importance': 'high', 'team_mode': True}
)
print(f"快照ID: {result['snapshot_id']}")
print(f"节点数: {result['node_count']}")

# 搜索记忆
results = await manager.search_memories(
    query='user authentication',
    search_options={'local': True, 'central': True, 'limit': 10}
)

# 分析模式
patterns = await manager.analyze_patterns()
for rec in patterns['recommendations']:
    print(f"建议: {rec}")
```

### MCP工具使用

```python
from src.mcp_core.memory_mcp_tools import get_memory_tool_dispatcher

dispatcher = get_memory_tool_dispatcher()

# 创建快照
result = await dispatcher.dispatch('create_memory_snapshot', {
    'project_path': '/path/to/project',
    'trigger': 'milestone',
    'importance': 'high',
    'team_mode': True
})

# 搜索记忆
result = await dispatcher.dispatch('search_memories', {
    'project_path': '/path/to/project',
    'query': 'authentication',
    'search_local': True,
    'search_central': True
})

# 获取统计
result = await dispatcher.dispatch('get_memory_statistics', {
    'project_path': '/path/to/project'
})
```

## 测试

运行集成测试:

```bash
cd /path/to/MCP
python -m pytest tests/test_hybrid_integration.py -v
```

或直接执行:

```bash
python tests/test_hybrid_integration.py
```

## 优势总结

1. **本地高性能**: SQLite提供毫秒级响应，无网络延迟
2. **团队共享**: MySQL支持团队协作，共享洞察和模式
3. **智能同步**: 自动/手动同步，支持离线工作
4. **统一接口**: IntegratedMemoryManager提供一致的API
5. **图谱分析**: 深度集成ProjectMemorySystem的图谱能力
6. **模式识别**: 结合本地、全局和团队模式分析
7. **MCP集成**: 10个MCP工具供AI助手调用

## 文件清单

| 文件 | 描述 |
|------|------|
| `src/mcp_core/services/hybrid_storage_system.py` | 混合存储系统实现 |
| `src/mcp_core/services/memory_hybrid_integration.py` | 集成记忆管理器 |
| `src/mcp_core/services/project_memory_system.py` | 项目记忆系统 |
| `src/mcp_core/memory_mcp_tools.py` | MCP工具定义与实现 |
| `tests/test_hybrid_integration.py` | 综合集成测试 |
| `docs/HYBRID_MEMORY_INTEGRATION.md` | 本文档 |

## 版本历史

- v1.0.0 (2025-11-21): 初始版本
  - 完成HybridStorageManager实现
  - 完成IntegratedMemoryManager集成
  - 添加10个MCP工具
  - 添加综合集成测试
  - 完成文档编写
