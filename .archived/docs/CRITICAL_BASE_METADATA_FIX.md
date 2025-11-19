# 🚨 MCP v2.0.0 - 紧急修复：多个Base元数据冲突

**日期**: 2025-01-19
**优先级**: 🔴 严重
**影响**: 所有跨服务的数据库操作

---

## 🐛 核心问题

### 错误现象
```
Foreign key associated with column 'project_sessions.project_id'
could not find table 'code_projects'
```

### 根本原因

**每个服务文件都创建了自己的 `Base`**:

```python
# code_knowledge_service.py
Base = declarative_base()  # Base #1

# project_context_service.py
Base = declarative_base()  # Base #2 (不同的元数据!)

# quality_guardian_service.py
Base = declarative_base()  # Base #3
```

**后果**:
- `CodeProject` (Base #1) 和 `ProjectSession` (Base #2) 在不同的元数据中
- SQLAlchemy无法识别它们之间的外键关系
- 运行时报错: "找不到表"

---

## ✅ 快速修复 (已应用)

###修复1: 异常时自动回滚

**文件**: `mcp_server_unified.py:304-319`

```python
except Exception as e:
    # 回滚会话以清除错误状态
    try:
        self.db_session.rollback()
        self.logger.warning("会话已回滚")
    except:
        pass

    self.logger.error(f"工具执行失败: {e}", exc_info=True)
    return {...}
```

**效果**:
- 任何工具失败后自动清理会话
- 后续工具调用不受影响
- ⚠️ 治标不治本

### 修复2: IntegrityError处理

**文件**: `mcp_server_unified.py:363-371`

```python
except IntegrityError:
    self.db_session.rollback()
    self.logger.info(f"项目已存在,将更新: {project_id}")
```

---

## 🔧 根治方案 (待实施)

### 方案A: 统一Base (推荐)

创建 `src/mcp_core/models/base.py`:
```python
from sqlalchemy.ext.declarative import declarative_base

# 全局唯一Base
Base = declarative_base()
```

修改所有服务文件:
```python
# 从统一位置导入
from mcp_core.models.base import Base

# 不要再创建新的Base!
# Base = declarative_base()  # ❌ 删除这行
```

### 方案B: 表反射 (备选)

```python
from sqlalchemy import MetaData, Table

metadata = MetaData()
code_projects = Table('code_projects', metadata, autoload_with=engine)
```

---

## 🚀 立即行动

### 步骤1: 重启服务器 (必须)

```bash
cd /Users/mac/Downloads/MCP

# 停止旧服务器
ps aux | grep mcp_server_enterprise | grep -v grep | awk '{print $2}' | xargs kill

# 启动新服务器
./restart_server.sh
```

### 步骤2: 验证修复

```bash
# 等待启动
sleep 8

# 测试健康检查
curl http://localhost:8765/health | python3 -m json.tool

# 查看日志
tail -f enterprise_server.log
```

### 步骤3: 测试MCP工具

重启Claude Code客户端，然后测试:
1. `analyze_codebase` - 应该成功
2. `start_dev_session` - 应该成功
3. `query_architecture` - 应该成功

---

## 📊 技术细节

### SQLAlchemy元数据隔离

```python
# 问题代码
Base1 = declarative_base()  # 元数据1
Base2 = declarative_base()  # 元数据2 (独立的!)

class CodeProject(Base1):  # 在元数据1中
    __tablename__ = "code_projects"

class ProjectSession(Base2):  # 在元数据2中
    __tablename__ = "project_sessions"
    project_id = Column(..., ForeignKey('code_projects.project_id'))
    # ❌ code_projects不在Base2的元数据中!
```

### 正确做法

```python
# 统一Base
from shared_module import Base

class CodeProject(Base):  # ✅ 同一个Base
    __tablename__ = "code_projects"

class ProjectSession(Base):  # ✅ 同一个Base
    __tablename__ = "project_sessions"
    project_id = Column(..., ForeignKey('code_projects.project_id'))
    # ✅ 外键可以正确识别
```

---

## 🎯 当前状态

### 已修复
- ✅ 异常自动回滚
- ✅ IntegrityError处理
- ✅ 服务器可以继续运行

### 待修复 (长期)
- ⚠️ 统一Base元数据
- ⚠️ 重构模型导入
- ⚠️ 添加单元测试

### 影响
- 🟡 **当前**: 可用,但可能偶尔出错
- 🟢 **修复后**: 完全稳定

---

## 📝 修改文件列表

1. `mcp_server_unified.py` ✅
   - Lines 304-319: 异常自动回滚
   - Lines 363-371: IntegrityError处理

2. `restart_server.sh` ✅
   - 重启脚本

3. `docs/CRITICAL_BASE_METADATA_FIX.md` ✅ (本文档)
   - 问题分析和解决方案

---

## ⚡ 紧急重启命令

```bash
# 一键重启 (在MCP目录下执行)
./restart_server.sh

# 或手动
kill $(ps aux | grep mcp_server_enterprise | grep -v grep | awk '{print $2}')
export DB_PASSWORD="Wxwy.2025@#"
nohup python3 mcp_server_enterprise.py --host 0.0.0.0 --port 8765 > enterprise_server.log 2>&1 &
```

---

**✨ 快速修复已应用！请重启服务器后重试！**

**重启**: `./restart_server.sh`
**验证**: `curl http://localhost:8765/health`
