# MCP v2.0.0 - 会话回滚问题完整解决方案

**问题**: 重复调用MCP工具导致 `Session's transaction has been rolled back` 错误
**日期**: 2025-01-19
**状态**: ✅ 已修复,需要重启服务器

---

## 🚨 问题现象

### 用户看到的错误
```
Error: {"success": false, "error": "This Session's transaction has been
rolled back due to a previous exception during flush. To begin a new
transaction with this Session, first issue Session.rollback(). Original
exception was: Foreign key associated with column 'project_sessions.project_id'
could not find table 'code_projects'..."}
```

### 触发条件
1. 调用 `analyze_codebase` 分析已存在的项目
2. 后续所有MCP工具调用都失败
3. 即使重启Claude Code客户端也无效
4. **必须重启MCP服务器**

---

## 🔍 问题诊断

### 步骤1: 检查服务器状态
```bash
ps aux | grep mcp_server
# 输出: mcp_server_enterprise.py --host 0.0.0.0 --port 8765
```

### 步骤2: 检查数据库
```bash
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' mcp_db -e "
SELECT project_id, name, status, total_entities
FROM code_projects
ORDER BY created_at DESC LIMIT 5;"
```

**发现问题**:
- 项目存在,但 `total_entities = 0` (异常状态)
- 表明之前的分析失败

### 步骤3: 检查代码
```bash
grep -A 5 "except:" mcp_server_unified.py
```

**发现根本原因**:
```python
# ❌ 问题代码
except:
    pass  # 不回滚会话!
```

---

## ✅ 解决方案

### 方案1: 快速重启(立即生效)

1. **停止当前服务器**
   ```bash
   ps aux | grep mcp_server_enterprise | grep -v grep | awk '{print $2}' | xargs kill
   ```

2. **清理异常数据**
   ```bash
   docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' mcp_db -e "
   DELETE FROM code_projects WHERE total_entities = 0;
   "
   ```

3. **使用重启脚本**
   ```bash
   cd /Users/mac/Downloads/MCP
   ./restart_server.sh
   ```

   或手动重启:
   ```bash
   export DB_PASSWORD="Wxwy.2025@#"
   python3 mcp_server_enterprise.py \
       --host 0.0.0.0 \
       --port 8765 \
       --rate-limit 100 \
       --max-connections 1000 \
       > enterprise_server.log 2>&1 &
   ```

4. **验证修复**
   ```bash
   # 等待8秒启动
   sleep 8

   # 测试健康检查
   curl http://localhost:8765/health | python3 -m json.tool
   ```

### 方案2: 完整验证

1. **重启Claude Code客户端** (确保重新连接)

2. **测试MCP工具**
   - 尝试 `analyze_codebase`
   - 应该可以正常工作

3. **检查日志**
   ```bash
   tail -f enterprise_server.log
   # 应该看到: "项目已存在,将更新: xxx"
   ```

---

## 📊 代码修复详情

### 修复文件
- `mcp_server_unified.py` (Lines 347-385)

### 修复前
```python
def _call_code_tool(self, tool_name: str, args: Dict) -> Dict:
    if tool_name == "analyze_codebase":
        try:
            self.code_service.create_project(...)
        except:
            pass  # ❌ 不回滚会话

        # 继续执行分析...
```

### 修复后
```python
def _call_code_tool(self, tool_name: str, args: Dict) -> Dict:
    if tool_name == "analyze_codebase":
        from sqlalchemy.exc import IntegrityError

        try:
            self.code_service.create_project(...)
        except IntegrityError:
            self.db_session.rollback()  # ✅ 立即回滚
            self.logger.info(f"项目已存在,将更新: {project_id}")
        except Exception as e:
            self.db_session.rollback()  # ✅ 其他错误也回滚
            self.logger.error(f"创建项目失败: {e}")
            raise

        # 继续执行分析...
```

---

## 🎯 关键改进

### 1. 精确异常处理
```python
# ✅ 只捕获预期的IntegrityError
except IntegrityError:
    # 处理重复记录
```

### 2. 立即回滚会话
```python
# ✅ 清除错误状态
self.db_session.rollback()
```

### 3. 日志记录
```python
# ✅ 记录发生了什么
self.logger.info(f"项目已存在,将更新: {project_id}")
```

### 4. 错误传播
```python
# ✅ 严重错误重新抛出
except Exception as e:
    self.db_session.rollback()
    raise
```

---

## 🔧 故障排查

### 问题: 重启后仍然失败

**检查1**: 代码是否更新?
```bash
grep "IntegrityError" mcp_server_unified.py
# 应该找到这个import
```

**检查2**: 进程是否使用新代码?
```bash
ps aux | grep mcp_server
# 查看启动时间,应该是最近
```

**检查3**: 数据库是否清理?
```bash
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' mcp_db -e "
SELECT * FROM code_projects WHERE total_entities = 0;"
# 应该返回空
```

### 问题: 外键错误 "could not find table"

**原因**: SQLAlchemy模型定义和数据库不一致

**解决**:
```bash
# 1. 验证表存在
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' mcp_db -e "SHOW TABLES;"

# 2. 重建外键
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/fix_foreign_keys.sql

# 3. 重启服务器
./restart_server.sh
```

---

## 📚 相关文档

- [SESSION_ROLLBACK_FIX_2025-01-19.md](SESSION_ROLLBACK_FIX_2025-01-19.md) - 详细技术分析
- [BUG_FIXES_2025-01-19.md](BUG_FIXES_2025-01-19.md) - 其他bug修复
- [scripts/cleanup_database.sql](../scripts/cleanup_database.sql) - 数据库清理
- [restart_server.sh](../restart_server.sh) - 快速重启脚本

---

## ✅ 验证清单

重启后,按以下步骤验证:

- [ ] 服务器进程运行中
- [ ] 健康检查返回200
- [ ] 日志中看到 "✅ 所有服务初始化完成"
- [ ] Claude Code客户端重新连接
- [ ] 可以调用 `analyze_codebase`
- [ ] 可以调用其他MCP工具
- [ ] 没有会话回滚错误

---

## 💡 预防措施

### 1. 添加幂等性
建议修改 `create_project` 支持 `if_not_exists`:
```python
def create_project(self, project_id: str, if_not_exists=True, **kwargs):
    if if_not_exists:
        existing = self.db.query(CodeProject).filter_by(project_id=project_id).first()
        if existing:
            return existing
    # 创建新项目...
```

### 2. 监控异常记录
定期运行:
```bash
docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/cleanup_database.sql
```

### 3. 添加单元测试
```python
def test_analyze_codebase_duplicate():
    # 第一次分析
    result1 = mcp_server.handle_request({
        "method": "tools/call",
        "params": {"name": "analyze_codebase", ...}
    })
    assert result1["result"]["success"]

    # 重复分析(应该成功)
    result2 = mcp_server.handle_request({
        "method": "tools/call",
        "params": {"name": "analyze_codebase", ...}
    })
    assert result2["result"]["success"]
```

---

**✨ 修复完成! 请重启服务器后重试您的MCP操作。**

**重启命令**: `./restart_server.sh`
**验证命令**: `curl http://localhost:8765/health`
