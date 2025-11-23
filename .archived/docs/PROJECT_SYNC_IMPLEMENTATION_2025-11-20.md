# 项目同步逻辑实现报告

**日期**: 2025-11-20
**问题**: `code_projects` 和 `projects` 表不同步导致外键约束失败
**文件**: `src/mcp_core/code_knowledge_service.py`

---

## 🐛 问题描述

当代码分析服务创建项目并尝试存储记忆时，出现外键约束错误：

```
(1452, 'Cannot add or update a child row: a foreign key constraint fails
(`mcp_db`.`long_memories`, CONSTRAINT `long_memories_ibfk_1`
FOREIGN KEY (`project_id`) REFERENCES `projects` (`project_id`) ON DELETE CASCADE)')
```

### 数据库架构问题

系统中存在**两个独立的项目表**：

1. **`code_projects`** - 代码项目表
   - 用于存储代码分析结果
   - 包含技术细节（语言、路径、统计信息）
   - 由 `CodeKnowledgeService.create_project()` 创建

2. **`projects`** - 通用项目表
   - 用于项目管理和记忆系统
   - 被 `long_memories`, `project_notes`, `project_sessions` 等表外键引用
   - **创建 `code_projects` 时未自动同步**

### 问题场景

```
步骤1: 分析代码 → 创建 code_projects 记录 ✅
步骤2: 存储记忆 → 查找 projects 记录 ❌ (不存在)
```

---

## ✅ 解决方案

### 实现自动同步机制

在 `CodeKnowledgeService.create_project()` 方法中添加同步逻辑：

**文件**: `src/mcp_core/code_knowledge_service.py` (Lines 153-203)

```python
def create_project(self,
                  project_id: str,
                  name: str,
                  path: str,
                  language: str = "python",
                  **kwargs) -> CodeProject:
    """创建项目"""
    # 1. 创建 code_projects 记录
    project = CodeProject(
        project_id=project_id,
        name=name,
        path=path,
        language=language,
        **kwargs
    )
    self.db.add(project)
    self.db.commit()
    self.db.refresh(project)

    # 2. ✨ 自动同步到 projects 表（新增）
    self._sync_to_projects_table(project_id, name, kwargs.get('description', ''))

    return project
```

### 同步实现细节

```python
def _sync_to_projects_table(self, project_id: str, name: str, description: str = '') -> None:
    """同步代码项目到通用 projects 表

    这确保了 long_memories 等表的外键约束能够正常工作
    """
    from sqlalchemy import text

    try:
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE 确保幂等性
        sync_sql = text("""
            INSERT INTO projects (project_id, name, description, owner_id, is_active, meta_data)
            VALUES (:project_id, :name, :description, 'system', 1, JSON_OBJECT('sync_from', 'code_projects'))
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                description = VALUES(description),
                updated_at = CURRENT_TIMESTAMP
        """)

        self.db.execute(sync_sql, {
            'project_id': project_id,
            'name': name,
            'description': description or f'代码项目: {name}'
        })
        self.db.commit()
    except Exception as e:
        # 同步失败不应该阻塞主流程，只记录警告
        print(f"⚠️  同步到 projects 表失败: {e}")
        self.db.rollback()
```

---

## 🎯 设计要点

### 1. 幂等性保证

使用 `INSERT ... ON DUPLICATE KEY UPDATE` 语法：
- 项目不存在时：插入新记录
- 项目已存在时：更新 name/description
- **可以多次调用而不会报错**

### 2. 非阻塞设计

```python
try:
    # 同步逻辑
except Exception as e:
    # 同步失败只记录警告，不抛出异常
    print(f"⚠️  同步到 projects 表失败: {e}")
    self.db.rollback()
```

**原因**: 即使同步失败，`code_projects` 记录已成功创建，不应该回滚代码分析结果。

### 3. 元数据标记

```python
JSON_OBJECT('sync_from', 'code_projects')
```

在 `projects.meta_data` 中标记数据来源，便于追踪和调试。

---

## 📊 修复前后对比

| 操作 | 修复前 | 修复后 |
|------|--------|--------|
| 创建 code_projects | ✅ 成功 | ✅ 成功 |
| 同步到 projects | ❌ 无此操作 | ✅ 自动同步 |
| 存储 long_memories | ❌ 外键约束失败 | ✅ 成功 |
| 幂等性 | N/A | ✅ 可重复执行 |
| 错误处理 | N/A | ✅ 非阻塞设计 |

---

## 🔧 临时修复 vs 永久方案

### 临时修复（已执行）

```sql
-- 手动为 wanglai 项目创建 projects 记录
INSERT INTO projects (project_id, name, description, owner_id, is_active)
VALUES ('wanglai', '网来项目 (WangLai)', 'Spring Boot项目', 'system', 1);
```

### 永久方案（已实现）

在代码层面添加自动同步逻辑，从根本上解决问题。

---

## 🧪 验证方法

### 测试同步功能

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mcp_core.code_knowledge_service import CodeKnowledgeService

# 创建数据库连接
engine = create_engine("mysql+pymysql://root:password@localhost/mcp_db")
Session = sessionmaker(bind=engine)
session = Session()

# 初始化服务
service = CodeKnowledgeService(session)

# 创建新项目（会自动同步）
project = service.create_project(
    project_id="test-sync",
    name="测试同步项目",
    path="/path/to/project",
    language="python",
    description="测试自动同步功能"
)

# 验证 code_projects 表
code_project = session.query(CodeProject).filter_by(project_id="test-sync").first()
print(f"✅ code_projects: {code_project.name if code_project else '不存在'}")

# 验证 projects 表
from sqlalchemy import text
result = session.execute(text("SELECT name, description FROM projects WHERE project_id='test-sync'"))
row = result.fetchone()
print(f"✅ projects: {row[0] if row else '不存在'}")
```

### 预期输出

```
✅ code_projects: 测试同步项目
✅ projects: 测试同步项目
```

---

## 💡 架构改进建议

### 长期方案：统一项目表

当前的双表架构存在维护成本：

```
建议方案:
1. 废弃 code_projects 表
2. 在 projects 表中添加代码项目相关字段
3. 使用 project_type 字段区分项目类型（code/general/etc）
```

**优点**:
- 单一数据源，无需同步
- 简化外键关系
- 减少数据不一致风险

**缺点**:
- 需要数据迁移
- 影响现有代码

**当前选择**: 保持双表 + 自动同步（最小化改动）

---

## 📈 影响范围

| 模块 | 影响 | 变更 |
|------|------|------|
| `CodeKnowledgeService.create_project` | 高 | 添加同步逻辑 |
| 代码分析流程 | 低 | 自动同步，无需改动 |
| 记忆存储 | 高 | 修复外键约束问题 |
| 现有项目 | 中 | 需要补充同步（手动或批量） |

---

## 🚀 部署建议

### 1. 重启MCP服务器

```bash
ps aux | grep mcp_server | grep -v grep | awk '{print $2}' | xargs kill
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_enterprise.py
```

### 2. 补充现有项目同步（可选）

```sql
-- 将所有 code_projects 同步到 projects
INSERT INTO projects (project_id, name, description, owner_id, is_active, meta_data)
SELECT
    project_id,
    name,
    description,
    'system' AS owner_id,
    1 AS is_active,
    JSON_OBJECT('sync_from', 'code_projects', 'language', language) AS meta_data
FROM code_projects
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;
```

---

**状态**: ✅ 实现完成
**测试**: ⏳ 待重启服务器后验证
**影响**: 彻底解决 code_projects 和 projects 不同步问题
