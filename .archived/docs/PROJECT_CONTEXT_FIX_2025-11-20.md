# Project Context Tables 修复报告

**日期**: 2025-11-20
**问题**: Session回滚导致6个MCP工具无法使用
**根因**: 首次插入 `project_notes` 失败，导致SQLAlchemy Session进入污染状态

---

## 🐛 问题分析

### 错误信息
```
This Session's transaction has been rolled back due to a previous exception during flush.
Original exception: (1054, "Unknown column 'session_id' in 'field list'")
```

### 影响范围
6个MCP工具完全无法使用：
- `add_project_note` - 添加项目笔记
- `create_todo` - 创建TODO
- `list_project_notes` - 列出笔记
- `list_todos` - 列出TODO
- `list_design_decisions` - 列出设计决策（被事务回滚影响）
- `get_project_context` - 获取项目上下文（被事务回滚影响）

---

## ✅ 修复验证

### 1. project_notes 表 - 完整

```bash
$ docker exec -i mcp-mysql mysql -uroot -p"Wxwy.2025@#" mcp_db -e "SHOW COLUMNS FROM project_notes;"
```

**结果**: 17个字段全部存在 ✅
- ✅ `session_id` VARCHAR(64) - 外键到 project_sessions
- ✅ `related_code` TEXT
- ✅ `related_entities` JSON
- ✅ `related_files` JSON
- ✅ `is_resolved` TINYINT(1)
- ✅ `resolved_at` DATETIME
- ✅ `resolved_note` TEXT
- ✅ `importance` INT (已从VARCHAR修改为INT)
- ✅ `created_at` / `updated_at` DATETIME

### 2. development_todos 表 - 完整

```bash
$ docker exec -i mcp-mysql mysql -uroot -p"Wxwy.2025@#" mcp_db -e "SHOW COLUMNS FROM development_todos;"
```

**结果**: 21个字段全部存在 ✅
- ✅ `session_id` VARCHAR(64) - 外键到 project_sessions
- ✅ `category` VARCHAR(64)
- ✅ `estimated_difficulty` INT
- ✅ `progress` INT
- ✅ `blocks` JSON
- ✅ `related_entities` JSON
- ✅ `related_files` JSON
- ✅ `completion_note` TEXT
- ✅ `priority` INT (已从VARCHAR修改为INT)
- ✅ `updated_at` DATETIME (新增)

---

## 🔧 修复方法

### Schema已完整，只需清理Session状态

**数据库Schema已100%正确**，问题在于：
1. 之前的 `scripts/fix_all_schemas.sql` 已经添加了所有缺失字段
2. 但由于首次插入失败，**SQLAlchemy Session进入回滚状态**
3. Session状态在内存中，不会自动恢复

### 解决方案：重启MCP服务器

```bash
# 方法1: 杀掉所有mcp_server进程
ps aux | grep mcp_server | grep -v grep | awk '{print $2}' | xargs kill

# 方法2: 使用重启脚本
./restart_server_complete.sh

# 方法3: 手动重启
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_enterprise.py
```

---

## 📊 修复前后对比

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| project_notes.session_id | ❌ 缺失 | ✅ 存在 |
| project_notes 其他字段 | ❌ 缺7个 | ✅ 完整(17) |
| development_todos.session_id | ❌ 缺失 | ✅ 存在 |
| development_todos 其他字段 | ❌ 缺8个 | ✅ 完整(21) |
| Session状态 | ❌ 回滚污染 | ⚠️ 需重启 |
| 6个MCP工具 | ❌ 全部失败 | ⏳ 重启后恢复 |

---

## 📝 SQL修复脚本

虽然Schema已完整，但为记录保留完整的修复SQL:

**文件**: `scripts/fix_project_context_tables_2025-11-20.sql`

关键修复：
```sql
-- project_notes 添加缺失字段
ALTER TABLE project_notes
ADD COLUMN session_id VARCHAR(64) AFTER project_id,
ADD COLUMN related_code TEXT AFTER importance,
ADD COLUMN related_entities JSON AFTER related_code,
ADD COLUMN related_files JSON AFTER related_entities,
ADD COLUMN is_resolved TINYINT(1) DEFAULT 0 AFTER tags,
ADD COLUMN resolved_at DATETIME AFTER is_resolved,
ADD COLUMN resolved_note TEXT AFTER resolved_at;

-- 修改类型
ALTER TABLE project_notes MODIFY COLUMN importance INT DEFAULT 3;

-- development_todos 添加缺失字段
ALTER TABLE development_todos
ADD COLUMN session_id VARCHAR(64) AFTER project_id,
ADD COLUMN category VARCHAR(64) AFTER description,
ADD COLUMN estimated_difficulty INT DEFAULT 3 AFTER priority,
ADD COLUMN progress INT DEFAULT 0 AFTER status,
ADD COLUMN blocks JSON AFTER depends_on,
ADD COLUMN related_entities JSON AFTER blocks,
ADD COLUMN related_files JSON AFTER related_entities,
ADD COLUMN completion_note TEXT AFTER completed_at,
ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- 修改类型
ALTER TABLE development_todos
MODIFY COLUMN priority INT DEFAULT 3,
MODIFY COLUMN estimated_hours INT;
```

---

## 🎯 下一步行动

1. **立即重启MCP服务器** - 清理Session回滚状态
2. **测试6个MCP工具** - 验证功能恢复
3. **更新文档** - 记录本次修复

---

## 💡 深度思考：为什么会出现这个问题？

### 根本原因链
1. **数据库Schema漂移** - 代码模型定义与数据库实际表结构不一致
2. **缺少Schema验证** - 启动时没有检查表结构完整性
3. **Session回滚传播** - 首次错误污染了整个Session生命周期
4. **缺少Session重置** - 错误处理没有调用 `session.rollback()`

### 预防措施
1. **Schema同步检查** - 服务器启动时验证所有表结构
2. **自动迁移** - 使用Alembic管理Schema变更
3. **错误隔离** - 每个MCP工具调用使用独立Session
4. **健康检查** - 定期验证数据库连接和Schema

### 建议改进（未来）
```python
# 在服务器启动时添加Schema验证
def verify_database_schema(session):
    """验证所有表的字段完整性"""
    issues = []

    # 检查 project_notes
    result = session.execute(text("SHOW COLUMNS FROM project_notes"))
    columns = [row[0] for row in result]
    required = ['session_id', 'related_code', 'related_entities', ...]
    missing = set(required) - set(columns)
    if missing:
        issues.append(f"project_notes 缺少字段: {missing}")

    # 检查 development_todos
    # ... 类似检查

    if issues:
        logger.error(f"❌ 数据库Schema不完整:\n" + "\n".join(issues))
        raise RuntimeError("请运行 scripts/fix_all_schemas.sql 修复")

    logger.info("✅ 数据库Schema验证通过")
```

---

**状态**: ✅ Schema修复完成，⏳ 等待重启服务器
**影响**: 重启后6个MCP工具将完全恢复正常
**测试**: 重启后请测试 `add_project_note` 和 `create_todo`
