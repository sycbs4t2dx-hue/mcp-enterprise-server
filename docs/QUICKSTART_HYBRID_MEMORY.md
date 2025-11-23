# 混合记忆存储系统 - 快速开始指南

## 30秒快速开始

```python
import asyncio
from src.mcp_core.services import create_integrated_manager

async def quick_start():
    # 1. 创建管理器
    manager = create_integrated_manager(
        project_path="/path/to/your/project",
        storage_mode='hybrid'  # 本地SQLite + 团队MySQL
    )

    # 2. 创建第一个快照
    result = await manager.create_snapshot(
        trigger='manual',
        context={'reason': '初始快照'},
        sync_options={'importance': 'high', 'team_mode': False}
    )
    print(f"✓ 快照创建: {result['snapshot_id']}")
    print(f"  节点数: {result['node_count']}")
    print(f"  洞察: {result['insights']}")

    # 3. 搜索记忆
    results = await manager.search_memories(
        query='authentication',
        search_options={'local': True, 'limit': 5}
    )
    print(f"✓ 搜索到 {len(results)} 个结果")

    # 4. 查看统计
    stats = manager.get_statistics()
    print(f"✓ 本地快照: {stats['storage']['local']['total_count']}")

asyncio.run(quick_start())
```

## 使用MCP工具 (供AI助手调用)

```python
import asyncio
from src.mcp_core.memory_mcp_tools import get_memory_tool_dispatcher

async def mcp_demo():
    dispatcher = get_memory_tool_dispatcher()

    # 创建快照
    result = await dispatcher.dispatch('create_memory_snapshot', {
        'project_path': '/path/to/project',
        'trigger': 'milestone',
        'importance': 'high'
    })
    print(f"✓ {result['message']}")

    # 搜索记忆
    result = await dispatcher.dispatch('search_memories', {
        'project_path': '/path/to/project',
        'query': 'user service',
        'search_local': True
    })
    print(f"✓ 找到 {result['total']} 个结果")

    # 分析模式
    result = await dispatcher.dispatch('analyze_memory_patterns', {
        'project_path': '/path/to/project'
    })
    if result['success']:
        for rec in result['recommendations'][:3]:
            print(f"  推荐: {rec}")

asyncio.run(mcp_demo())
```

## 运行集成测试

```bash
# 进入项目目录
cd /path/to/MCP

# 运行测试
python tests/test_hybrid_integration.py

# 预期输出:
# ======================================================================
# 混合记忆存储系统 - 综合集成测试
# ======================================================================
# ...
# 测试总结
# ======================================================================
# 总测试数: 8
# 通过: 8
# 失败: 0
# 成功率: 100.0%
# ======================================================================
```

## 10个MCP工具速查

| 工具 | 用途 | 示例 |
|------|------|------|
| `create_memory_snapshot` | 创建快照 | 里程碑、提交、发布时保存状态 |
| `search_memories` | 搜索记忆 | 查找历史代码、文档、决策 |
| `recover_memory_by_similarity` | 相似度恢复 | 找到相似的历史状态 |
| `get_file_memory_history` | 文件历史 | 追踪文件演变 |
| `sync_memories_to_team` | 同步团队 | 上传到MySQL共享 |
| `share_insight` | 分享洞察 | 分享发现给团队 |
| `get_team_insights` | 团队洞察 | 查看团队分享 |
| `analyze_memory_patterns` | 模式分析 | 识别代码模式 |
| `get_memory_statistics` | 查看统计 | 监控系统状态 |
| `cleanup_old_memories` | 清理旧数据 | 释放存储空间 |

## 存储位置

```
your-project/
├── .mcp_memory/
│   ├── local.db           # 本地SQLite数据库
│   └── project_memory/    # 项目记忆图谱
│       ├── memory.db
│       └── snapshot_*.pkl
```

## 配置团队模式

```bash
# 设置环境变量
export MCP_TEAM_MODE=true
export MCP_TEAM_ID=your_team_id

# 或在代码中
import os
os.environ['MCP_TEAM_MODE'] = 'true'
os.environ['MCP_TEAM_ID'] = 'team_001'
```

## 常见问题

### Q: 如何只使用本地存储?

```python
manager = create_integrated_manager(
    project_path="/path/to/project",
    storage_mode='local'  # 纯本地模式
)
```

### Q: 如何强制同步到团队?

```python
result = await manager.sync_to_team()
print(f"同步了 {result['synced_count']} 个快照")
```

### Q: 如何清理旧数据?

```python
# 清理30天前的数据
result = await manager.cleanup(days=30)
print(f"清理了 {result['deleted_count']} 个快照")
```

## 下一步

- 阅读完整文档: `docs/HYBRID_MEMORY_INTEGRATION.md`
- 查看源码: `src/mcp_core/services/memory_hybrid_integration.py`
- 运行测试: `tests/test_hybrid_integration.py`
- 探索MCP工具: `src/mcp_core/memory_mcp_tools.py`

## 联系支持

遇到问题? 查看:
- 日志文件: `logs/mcp_server.log`
- 错误追踪: `src/mcp_core/common/logger.py`
- 数据库状态: 运行 `get_memory_statistics` 工具
