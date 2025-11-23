# AI辅助项目持续开发系统 - 实现文档

> 基于Claude Code能力 + MCP协议的项目可持续开发解决方案

**实现日期**: 2025-01-19
**版本**: v1.5.0

---

## 🎯 系统概述

### 核心目标

解决项目烂尾的根本问题：
- ❌ **上下文丢失** → ✅ 持久化会话和决策记录
- ❌ **知识碎片化** → ✅ 代码知识图谱 + AI理解
- ❌ **复杂度失控** → ✅ 智能质量监控
- ❌ **缺乏持续性** → ✅ 智能TODO管理 + 会话恢复

### 核心理念

```
人类开发者 + AI助手 + MCP持久化记忆 = 永不烂尾的项目
```

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              开发者 (通过Claude Code/Desktop)              │
└────────────────────┬────────────────────────────────────┘
                     │ MCP协议
                     ↓
┌─────────────────────────────────────────────────────────┐
│         AI辅助开发中枢 (MCP Server)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────┐ │
│  │代码知识图谱     │  │项目上下文管理   │  │AI理解引擎 │ │
│  │- Python/Java   │  │- 会话记录      │  │- Claude  │ │
│  │- Vue/多语言    │  │- 设计决策      │  │- 代码理解 │ │
│  │- 调用关系      │  │- TODO管理     │  │- TODO生成│ │
│  └────────────────┘  └────────────────┘  └──────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              MCP工具集 (20+工具)                    │ │
│  │  - 代码分析工具 (8个)                               │ │
│  │  - 上下文管理工具 (12个)                            │ │
│  │  - AI辅助工具 (7个)                                 │ │
│  └────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│              持久化存储 (MySQL)                           │
│  - code_projects, code_entities, code_relations         │
│  - project_sessions, design_decisions                   │
│  - project_notes, development_todos                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🗄️ 数据模型

### 1. 代码知识图谱 (已有)

```sql
-- 项目信息
code_projects (project_id, name, path, language, total_entities...)

-- 代码实体 (类、函数、方法等)
code_entities (entity_id, project_id, type, name, file_path, line_number...)

-- 代码关系 (调用、继承、导入等)
code_relations (relation_id, project_id, source_id, target_id, relation_type...)

-- 高层次知识
code_knowledge (knowledge_id, project_id, category, title, description...)
```

### 2. 项目上下文管理 (新增)

```sql
-- 开发会话
project_sessions (
    session_id, project_id,
    start_time, end_time, duration_minutes,
    goals, achievements, next_steps, context_summary,
    files_modified, issues_encountered, todos_completed
)

-- 设计决策
design_decisions (
    decision_id, project_id, session_id,
    category, title, description, reasoning,
    alternatives, trade_offs, impact_scope,
    status, superseded_by
)

-- 项目笔记
project_notes (
    note_id, project_id, session_id,
    category, title, content, importance,
    related_code, related_entities, tags,
    is_resolved, resolved_at
)

-- 开发TODO
development_todos (
    todo_id, project_id, session_id,
    title, description, category,
    priority, estimated_difficulty, estimated_hours,
    status, progress,
    depends_on, blocks,
    completed_at, completion_note
)
```

---

## 🔧 核心功能实现

### 1. 项目上下文管理器

**文件**: `src/mcp_core/project_context_service.py` (750行)

**核心类**: `ProjectContextManager`

**主要方法**:

```python
# 会话管理
start_session(project_id, goals) → ProjectSession
end_session(session_id, achievements, next_steps) → ProjectSession
get_last_session(project_id) → ProjectSession
update_session_summary(session_id, ai_summary) → None

# 设计决策
record_decision(project_id, title, reasoning, alternatives...) → DesignDecision
get_decisions(project_id, category) → List[DesignDecision]
supersede_decision(old_id, new_id) → None

# 项目笔记
add_note(project_id, category, title, content, importance...) → ProjectNote
get_notes(project_id, category, min_importance) → List[ProjectNote]
resolve_note(note_id, resolved_note) → None

# TODO管理
create_todo(project_id, title, priority, depends_on...) → DevelopmentTodo
update_todo_status(todo_id, status, progress) → DevelopmentTodo
get_next_todo(project_id) → DevelopmentTodo  # 考虑依赖关系

# 上下文恢复
generate_resume_context(project_id) → Dict  # 用于AI生成briefing
get_project_statistics(project_id) → Dict
```

**使用示例**:

```python
manager = ProjectContextManager(db)

# 开始会话
session = manager.start_session(
    project_id="my_project",
    goals="实现用户认证模块"
)

# 记录决策
decision = manager.record_decision(
    project_id="my_project",
    title="使用JWT进行身份认证",
    reasoning="JWT无状态，易于扩展",
    alternatives=[
        {"name": "Session", "pros": "简单", "cons": "有状态"}
    ]
)

# 创建TODO
todo = manager.create_todo(
    project_id="my_project",
    title="实现JWT生成和验证",
    priority=5,
    estimated_hours=2
)

# 结束会话
manager.end_session(
    session_id=session.session_id,
    achievements="完成JWT基础实现",
    next_steps="继续实现认证中间件"
)
```

### 2. AI辅助代码理解服务

**文件**: `src/mcp_core/ai_understanding_service.py` (850行)

**核心类**: `AICodeUnderstandingService`

**主要方法**:

```python
# 代码理解
understand_function(function_info, related_code) → str
understand_module(module_name, entities, relations) → str
explain_architecture(project_info) → str

# 会话摘要
generate_session_summary(session_info, files_modified, achievements) → str
generate_resumption_briefing(context) → str  # 核心功能！

# TODO管理
generate_todos_from_goal(goal, project_context) → List[Dict]
suggest_next_task(todos, recent_completed, developer_context) → Dict
decompose_task(complex_task) → List[Dict]

# 质量分析
analyze_code_quality(entity_stats, relation_stats, issues) → str
```

**集成Claude API**:

```python
import anthropic

ai_service = AICodeUnderstandingService(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-5-sonnet-20241022"
)

# AI理解函数
understanding = ai_service.understand_function({
    "name": "process_order",
    "signature": "def process_order(order_id: str) -> Order",
    "docstring": "处理订单逻辑",
    "file_path": "services/order_service.py"
})

# AI生成恢复briefing
context = context_manager.generate_resume_context(project_id)
briefing = ai_service.generate_resumption_briefing(context)
print(briefing)
# 输出:
# 欢迎回来！距离上次开发已经3天了。
#
# 上次开发状态:
# - 目标: 实现用户认证模块
# - 完成: JWT登录、权限检查 (70%)
# - 遇到问题: Redis连接不稳定
# ...
```

### 3. MCP工具集成

**文件**: `src/mcp_core/context_mcp_tools.py` (650行)

**上下文管理工具** (12个):

1. **start_dev_session** - 开始开发会话
2. **end_dev_session** - 结束会话并总结
3. **record_design_decision** - 记录设计决策
4. **add_project_note** - 添加项目笔记
5. **create_todo** - 创建TODO
6. **update_todo_status** - 更新TODO状态
7. **get_project_context** - 获取项目上下文（用于恢复）
8. **list_todos** - 列出TODO
9. **get_next_todo** - 获取建议的下一个TODO
10. **list_design_decisions** - 列出设计决策
11. **list_project_notes** - 列出项目笔记
12. **get_project_statistics** - 获取项目统计

**AI辅助工具** (7个):

1. **ai_understand_function** - AI理解函数
2. **ai_understand_module** - AI理解模块
3. **ai_explain_architecture** - AI解释架构
4. **ai_generate_resumption_briefing** - AI生成恢复briefing
5. **ai_generate_todos_from_goal** - AI从目标生成TODO
6. **ai_decompose_task** - AI分解复杂任务
7. **ai_analyze_code_quality** - AI分析代码质量

**工具定义示例**:

```python
{
    "name": "get_project_context",
    "description": "获取项目当前上下文，包括最近的会话、进行中的TODO、未解决的问题等。用于快速恢复开发状态。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "项目ID"
            }
        },
        "required": ["project_id"]
    }
}
```

---

## 🎬 实际使用场景

### 场景1: 开始新功能开发

```
开发者: "我要实现用户权限管理功能"

AI (调用MCP工具):
1. start_dev_session(project_id, goals="实现RBAC权限管理")
2. record_design_decision(title="选择RBAC", reasoning="...")
3. add_project_note(category="pitfall", title="权限检查必须在后端")
4. ai_generate_todos_from_goal(goal="实现权限管理")
   → 生成5个详细TODO
5. get_next_todo() → 建议先实现数据库模型

开发者开始编码...
```

### 场景2: 中断后恢复 (核心场景！)

```
开发者: (3天后) "继续开发"

AI (调用MCP工具):
1. get_project_context(project_id)
   → 获取上次会话、进行中的TODO、未解决问题

2. ai_generate_resumption_briefing(context)
   → AI生成友好的恢复briefing

AI输出:
"""
欢迎回来！距离上次开发已经3天了。

上次开发状态 (2025-01-16):
✅ 已完成: 数据库模型设计、Role和Permission的CRUD API
⏸️  进行中: 权限装饰器实现 (70%)
❌ 遇到问题: 循环导入 (auth/decorators.py ↔ user_service.py)

代码变更:
- 新增: models/permission.py (156行)
- 修改: models/user.py (添加了roles关联)

下一步建议:
1. 解决循环导入问题 (使用延迟导入)
2. 完成@require_permission装饰器 (还需30分钟)
3. 添加单元测试

相关文件:
- auth/decorators.py:45 (装饰器实现到这里)
- tests/test_auth.py (需要添加测试)
"""

开发者可以立即继续，无缝衔接！
```

### 场景3: 遇到困难

```
开发者: "这个性能问题怎么解决？订单查询太慢了"

AI (调用MCP工具):
1. trace_calls(entity_id="order_query") → 分析调用链
2. find_dependencies(entity_id="order_query") → 找依赖
3. ai_understand_function(entity_id="order_query")
   → AI分析函数逻辑

AI输出:
"""
问题定位:
- 调用链: API → Service → Repository → SQL
- 发现: 无索引，N+1查询
- 影响: 3个高频API

解决方案:
✅ 方案A: 添加数据库索引 (快速，风险小)
   - 添加 order(user_id, created_at) 复合索引
   - 优化关联查询 (eager loading)

✅ 方案B: 引入缓存 (需考虑一致性)
   - Redis缓存订单列表 (1分钟TTL)

推荐: 方案A + 部分方案B
"""

4. create_todo(title="添加订单查询索引", priority=5)
5. record_design_decision(title="优化订单查询", reasoning="...")
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖（已有）
pip install sqlalchemy pymysql fastapi anthropic

# 多语言支持（可选）
pip install javalang  # Java支持
```

### 2. 初始化数据库

```bash
# 方式1: 使用初始化脚本
chmod +x init_ai_assisted_development.sh
./init_ai_assisted_development.sh

# 方式2: Python脚本
python3 test_ai_assisted_development.py
```

### 3. 配置Claude API

```bash
# 设置环境变量
export ANTHROPIC_API_KEY='your-api-key-here'

# 或在代码中设置
ai_service = AICodeUnderstandingService(api_key="your-key")
```

### 4. 在Claude Code/Desktop中使用

在MCP服务器配置中添加新工具：

```json
{
  "mcpServers": {
    "memory-with-ai": {
      "command": "python3",
      "args": [
        "/path/to/MCP/src/mcp_stdio_server.py"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

### 5. 开始使用

在Claude Code中:

```
你: "分析这个项目并记录架构"

Claude: 我来帮你分析项目:
1. 调用analyze_codebase分析代码
2. 调用ai_explain_architecture生成架构说明
3. 调用record_design_decision记录关键决策
✅ 完成！项目架构已记录到持久化存储。

你: "3天后，继续开发"

Claude: 欢迎回来！让我帮你恢复上下文...
调用get_project_context和ai_generate_resumption_briefing
[显示详细的恢复briefing]
建议下一步: 实现XXX功能
```

---

## 📈 系统优势

### 1. 上下文永不丢失

- ✅ 每次会话都有记录（时间、目标、成果）
- ✅ 设计决策有完整的reasoning
- ✅ 问题和坑都有记录
- ✅ AI可以生成恢复briefing

### 2. 知识沉淀自动化

- ✅ 代码知识图谱自动构建
- ✅ AI自动生成架构说明
- ✅ 设计决策持久化存储
- ✅ 笔记和经验积累

### 3. TODO智能管理

- ✅ AI从目标生成TODO
- ✅ 自动计算依赖关系
- ✅ 智能推荐下一步
- ✅ 进度可视化

### 4. AI深度理解

- ✅ 函数意图理解（不仅是语法）
- ✅ 模块职责分析
- ✅ 架构模式识别
- ✅ 质量问题预警

---

## 🎯 成功指标

### 项目不烂尾的标志

✅ **随时可恢复**: 中断1周后，5分钟内可恢复状态

✅ **进度可见**: 清楚知道完成了什么，还剩什么

✅ **质量可控**: 技术债务在可接受范围

✅ **知识沉淀**: 核心逻辑有文档，关键决策有记录

✅ **AI可理解**: AI能准确描述项目架构和当前状态

---

## 📊 项目进度

```
v1.0.0: REST API + 记忆管理 ✅
v1.1.0: MCP stdio协议 ✅
v1.2.0: 远程部署 ✅
v1.3.0: Python代码知识图谱 ✅
v1.4.0: 多语言支持 (Java + Vue) ✅
v1.5.0: AI辅助持续开发 ✅ ← 当前

进度: ███████████████████████████████ 95% (9/10)
```

---

## 🔮 下一步计划

### v1.6.0: 质量守护者

- [ ] 代码异味检测
- [ ] 技术债务评估
- [ ] 性能瓶颈预测
- [ ] 自动重构建议

### v1.7.0: 知识可视化

- [ ] 代码知识图谱可视化
- [ ] 项目时间线展示
- [ ] TODO甘特图
- [ ] 依赖关系图

### v1.8.0: 团队协作

- [ ] 多人会话支持
- [ ] 知识共享机制
- [ ] Code Review集成
- [ ] 冲突预警

---

## 📚 相关文档

- **AI_ASSISTED_DEVELOPMENT_DESIGN.md** - 完整设计文档
- **CODE_KNOWLEDGE_GRAPH_GUIDE.md** - 代码知识图谱使用指南
- **MULTI_LANGUAGE_DESIGN.md** - 多语言支持设计
- **RELEASE_v1.5.0.md** - 本版本发布说明

---

## 💡 核心创新点

### 1. AI理解层

**传统方式**: 代码 → 静态分析 → 结构化数据

**AI增强方式**:
```
代码 + 注释 + Git历史 + 开发记录
    ↓ Claude深度理解
语义理解 + 意图识别 + 架构洞察
    ↓
持久化到知识图谱
```

### 2. 上下文时间旅行

能力：回到任何开发时刻的理解状态

```python
context = load_context(date="2025-01-05")
AI重现: "2周前你正在实现支付模块，当时的设计思路是..."
```

### 3. 预测性维护

AI基于趋势分析，提前预警：
- 复杂度增长速度
- 技术债累积
- 性能下降趋势

---

**实现完成日期**: 2025-01-19
**核心功能**: 完整实现 ✅
**状态**: 可用于生产环境
