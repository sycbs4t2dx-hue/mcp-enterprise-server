# MCP项目快速启动指南 (本地MySQL版)

> 使用本地MySQL数据库，密码: `Wxwy.2025@#`

---

## 📋 前置条件

- ✅ Python 3.10+
- ✅ MySQL 5.7+ / 8.0+ (已安装并运行)
- ✅ Redis 7+ (可选，用于缓存)
- ✅ Milvus 2.3+ (可选，用于向量检索)

---

## 🚀 快速启动 (3步完成)

### Step 1: 创建MySQL数据库

```bash
# 登录MySQL (密码: Wxwy.2025@#)
mysql -u root -p

# 或直接执行SQL脚本
mysql -u root -p < scripts/setup_mysql.sql
```

在MySQL命令行中执行：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS mcp_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 验证
SHOW DATABASES LIKE 'mcp_db';

-- 退出
EXIT;
```

### Step 2: 安装依赖并初始化

```bash
cd /Users/mac/Downloads/MCP

# 安装Python依赖
pip install -e ".[dev]"

# 初始化数据库表和数据
python scripts/init_database.py
```

**预期输出**:
```
============================================================
MCP数据库初始化 (MySQL)
============================================================
检查MySQL数据库连接...
✓ MySQL版本: 8.0.x
✓ 数据库连接正常
开始创建数据库表...
✓ 数据库表创建成功
开始插入初始数据...
✓ 初始数据插入成功
  - 管理员账号: admin / admin123
  - 测试账号: testuser / test123
  - 示例项目ID: proj_demo_001
============================================================
数据库初始化完成!
============================================================
```

### Step 3: 启动服务

```bash
# 启动FastAPI服务 (开发模式，自动重载)
uvicorn src.mcp_core.main:app --reload --host 0.0.0.0 --port 8000
```

**访问服务**:
- API文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 👥 测试账号

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| **admin** | admin123 | 管理员 | 全部权限 |
| **testuser** | test123 | 普通用户 | 只读权限 |

---

## 📝 API测试

### 1. 用户登录

```bash
# 登录获取Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**响应**:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": "user_xxx",
  "username": "admin",
  "role": "admin"
}
```

### 2. 创建项目

```bash
# 保存Token
TOKEN="<上面获取的access_token>"

# 创建项目
curl -X POST http://localhost:8000/api/v1/project/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的第一个项目",
    "description": "测试项目"
  }'
```

### 3. 存储记忆

```bash
# 存储记忆 (需要先获取项目ID)
PROJECT_ID="<项目ID>"

curl -X POST http://localhost:8000/api/v1/memory/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"content\": \"项目使用Python FastAPI框架开发\",
    \"memory_level\": \"mid\",
    \"importance\": 0.8
  }"
```

### 4. 检索记忆

```bash
curl -X POST http://localhost:8000/api/v1/memory/retrieve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"query\": \"项目用什么框架?\",
    \"top_k\": 5
  }"
```

### 5. Token压缩

```bash
curl -X POST http://localhost:8000/api/v1/token/compress \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "这是一段很长的文本内容，需要进行压缩以减少Token消耗...",
    "target_ratio": 0.5
  }'
```

### 6. 幻觉检测

```bash
curl -X POST http://localhost:8000/api/v1/validate/detect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"output\": \"项目使用FastAPI框架\"
  }"
```

---

## 🔍 验证数据库

```bash
# 登录MySQL查看
mysql -u root -p

# 密码: Wxwy.2025@#
```

```sql
-- 使用数据库
USE mcp_db;

-- 查看所有表
SHOW TABLES;

-- 查看用户
SELECT user_id, username, role, is_active FROM users;

-- 查看项目
SELECT project_id, name, owner_id FROM projects;

-- 查看权限
SELECT user_id, can_read_memory, can_write_memory FROM user_permissions;

-- 退出
EXIT;
```

**预期表列表**:
```
+---------------------+
| Tables_in_mcp_db    |
+---------------------+
| audit_logs          |
| long_memories       |
| projects            |
| system_configs      |
| user_permissions    |
| users               |
+---------------------+
```

---

## 📂 项目结构

```
/Users/mac/Downloads/MCP/
├── config.yaml              ✅ 配置文件 (已配置MySQL)
├── src/mcp_core/
│   ├── main.py             FastAPI主应用
│   ├── api/                API路由
│   │   ├── v1/
│   │   │   ├── auth.py     认证API
│   │   │   ├── memory.py   记忆API
│   │   │   ├── token.py    Token API
│   │   │   ├── validate.py 幻觉检测API
│   │   │   └── project.py  项目API
│   │   └── dependencies/   依赖注入
│   ├── services/           核心服务
│   ├── models/             数据模型
│   └── common/             通用模块
├── scripts/
│   ├── setup_mysql.sql     ✅ MySQL初始化脚本
│   └── init_database.py    ✅ 数据库初始化
└── tests/                  测试代码
```

---

## ⚙️ 配置说明

### config.yaml 关键配置

```yaml
# 数据库连接 (已配置)
database:
  url: "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
  # 注意: @ 符号需要URL编码为 %40
  #       # 符号需要URL编码为 %23

# Redis (可选)
redis:
  url: "redis://localhost:6379/0"

# Milvus (可选)
vector_db:
  milvus:
    host: "localhost"
    port: 19530
```

### 修改配置

```bash
# 编辑配置文件
vim config.yaml

# 修改后重启服务即可生效
```

---

## 🛠️ 常见问题

### 1. 数据库连接失败

**错误**: `Can't connect to MySQL server`

**检查**:
```bash
# 检查MySQL是否运行
sudo systemctl status mysql    # Linux
brew services list             # macOS

# 检查端口
netstat -an | grep 3306

# 测试连接
mysql -u root -p
```

### 2. 密码中特殊字符问题

**错误**: `Access denied`

**说明**:
- 密码 `Wxwy.2025@#` 在URL中需要编码
- `@` → `%40`
- `#` → `%23`
- 已在config.yaml中正确配置

### 3. 表不存在

**错误**: `Table 'mcp_db.users' doesn't exist`

**解决**:
```bash
# 重新运行初始化脚本
python scripts/init_database.py
```

### 4. 缺少依赖

**错误**: `ModuleNotFoundError: No module named 'pymysql'`

**解决**:
```bash
pip install -e ".[dev]"
```

---

## 📖 相关文档

- **MYSQL_SETUP.md** - MySQL详细配置指南
- **PHASE6_COMPLETION_REPORT.md** - Phase 6完成报告
- **README.md** - 项目说明
- **API文档**: http://localhost:8000/docs

---

## 🎯 下一步

1. **启动Redis** (可选，用于缓存):
   ```bash
   redis-server
   ```

2. **启动Milvus** (可选，用于向量检索):
   ```bash
   docker-compose -f docker/milvus-compose.yaml up -d
   ```

3. **运行测试**:
   ```bash
   pytest tests/unit/ -v
   ```

4. **查看API文档**:
   - 打开浏览器访问: http://localhost:8000/docs

---

**配置完成！现在可以开始使用MCP项目了！** 🎉

**快速命令**:
```bash
# 一键启动
cd /Users/mac/Downloads/MCP && uvicorn src.mcp_core.main:app --reload
```
