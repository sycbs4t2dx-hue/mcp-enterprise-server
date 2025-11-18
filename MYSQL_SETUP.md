# MySQL数据库配置说明

> **更新时间**: 2025-01-18
> **数据库**: MySQL 5.7+ / 8.0+

---

## 📋 概述

MCP项目已从PostgreSQL迁移到MySQL数据库，使用PyMySQL驱动连接。

---

## 🔧 MySQL安装与配置

### 1. 安装MySQL

```bash
# macOS (Homebrew)
brew install mysql
brew services start mysql

# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql

# CentOS/RHEL
sudo yum install mysql-server
sudo systemctl start mysqld
```

### 2. 创建数据库和用户

```bash
# 登录MySQL
mysql -u root -p

# 在MySQL命令行中执行:
```

```sql
-- 创建数据库 (UTF8MB4编码,支持emoji和多语言)
CREATE DATABASE mcp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'mcp_password';

-- 授权
GRANT ALL PRIVILEGES ON mcp_db.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;

-- 验证
SHOW DATABASES;
SELECT user, host FROM mysql.user WHERE user='mcp_user';

-- 退出
EXIT;
```

### 3. 验证连接

```bash
# 使用新用户连接
mysql -u mcp_user -p mcp_db

# 输入密码: mcp_password
```

---

## 📦 Python依赖

### 安装数据库驱动

```bash
cd /Users/mac/Downloads/MCP

# 安装项目依赖(包含PyMySQL)
pip install -e ".[dev]"

# 或单独安装
pip install pymysql cryptography
```

**依赖说明**:
- `pymysql>=1.1.0` - MySQL数据库驱动
- `cryptography>=41.0.0` - 用于MySQL加密连接

---

## ⚙️ 配置文件

### 1. 数据库连接URL格式

```yaml
# config.yaml
database:
  url: "mysql+pymysql://mcp_user:mcp_password@localhost:3306/mcp_db?charset=utf8mb4"
```

**URL组成**:
- `mysql+pymysql://` - 驱动类型
- `mcp_user:mcp_password` - 用户名:密码
- `localhost:3306` - 主机:端口
- `mcp_db` - 数据库名
- `?charset=utf8mb4` - 字符集参数

### 2. 连接池配置

```yaml
database:
  pool_size: 20          # 连接池大小
  max_overflow: 10       # 最大溢出连接数
  pool_timeout: 30       # 连接超时(秒)
  pool_recycle: 3600     # 连接回收时间(秒)
  echo: false            # SQL日志
```

---

## 🗄️ 数据表结构

### 表列表 (6张表)

```
1. users             用户表
2. user_permissions  权限表
3. projects          项目表
4. long_memories     长期记忆表
5. audit_logs        审计日志表
6. system_configs    系统配置表
```

### 字符集配置

所有表使用:
- 字符集: `utf8mb4`
- 排序规则: `utf8mb4_unicode_ci`

支持存储emoji和各种Unicode字符。

---

## 🚀 初始化数据库

### 方式1: 使用初始化脚本 (推荐)

```bash
cd /Users/mac/Downloads/MCP

# 确保数据库已创建
mysql -u mcp_user -p mcp_db -e "SELECT 1"

# 运行初始化脚本
python scripts/init_database.py
```

**脚本功能**:
- ✅ 检测MySQL连接
- ✅ 创建所有数据表
- ✅ 创建管理员账号 (`admin / admin123`)
- ✅ 创建测试账号 (`testuser / test123`)
- ✅ 创建示例项目
- ✅ 插入默认配置

### 方式2: 使用Alembic迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head
```

---

## 📊 初始数据

### 默认用户

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin | admin123 | admin | 全部权限 |
| testuser | test123 | user | 只读权限 |

### 默认权限

**管理员权限** (admin):
- ✅ 读取记忆 (can_read_memory)
- ✅ 写入记忆 (can_write_memory)
- ✅ 删除记忆 (can_delete_memory)
- ✅ 读取项目 (can_read_project)
- ✅ 写入项目 (can_write_project)
- ✅ 删除项目 (can_delete_project)
- ✅ 管理用户 (can_manage_users)
- ✅ 查看统计 (can_view_stats)
- ✅ 导出数据 (can_export_data)

**测试用户权限** (testuser):
- ✅ 读取记忆
- ✅ 读取项目
- ✅ 查看统计
- ❌ 其他操作禁止

---

## 🔍 验证数据库

### 1. 检查表

```bash
mysql -u mcp_user -p mcp_db
```

```sql
-- 查看所有表
SHOW TABLES;

-- 输出应该包含:
-- +---------------------+
-- | Tables_in_mcp_db    |
-- +---------------------+
-- | users               |
-- | user_permissions    |
-- | projects            |
-- | long_memories       |
-- | audit_logs          |
-- | system_configs      |
-- +---------------------+

-- 查看表结构
DESCRIBE users;
DESCRIBE projects;

-- 查看初始数据
SELECT username, role FROM users;
SELECT name, owner_id FROM projects;
```

### 2. 测试连接

```python
# test_connection.py
from sqlalchemy import create_engine, text

url = "mysql+pymysql://mcp_user:mcp_password@localhost:3306/mcp_db?charset=utf8mb4"
engine = create_engine(url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT VERSION()"))
    print(f"MySQL version: {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM users"))
    print(f"Users count: {result.scalar()}")
```

---

## ⚠️ 常见问题

### 1. 连接失败

**错误**: `Can't connect to MySQL server`

**解决**:
```bash
# 检查MySQL是否运行
sudo systemctl status mysql    # Linux
brew services list             # macOS

# 检查端口
netstat -an | grep 3306

# 重启MySQL
sudo systemctl restart mysql
```

### 2. 认证失败

**错误**: `Access denied for user 'mcp_user'@'localhost'`

**解决**:
```sql
-- 重新创建用户
DROP USER IF EXISTS 'mcp_user'@'localhost';
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'mcp_password';
GRANT ALL PRIVILEGES ON mcp_db.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 字符集问题

**错误**: `Incorrect string value`

**解决**:
```sql
-- 检查数据库字符集
SHOW CREATE DATABASE mcp_db;

-- 修改为utf8mb4
ALTER DATABASE mcp_db CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- 修改表字符集
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. JSON列问题

**错误**: MySQL 5.5不支持JSON类型

**解决**:
- 升级到MySQL 5.7+
- 或将JSON列改为TEXT

---

## 🔐 安全建议

### 1. 修改默认密码

```sql
-- 修改数据库用户密码
ALTER USER 'mcp_user'@'localhost' IDENTIFIED BY 'your_strong_password';

-- 修改应用管理员密码
-- 在应用中登录后修改
```

### 2. 生产环境配置

```yaml
# config.production.yaml
database:
  # 使用环境变量
  url: "${DATABASE_URL}"

  # 或使用加密配置
  host: "${DB_HOST}"
  port: "${DB_PORT}"
  username: "${DB_USER}"
  password: "${DB_PASSWORD}"
  database: "${DB_NAME}"
```

### 3. 权限最小化

```sql
-- 生产环境只授予必要权限
GRANT SELECT, INSERT, UPDATE, DELETE ON mcp_db.* TO 'mcp_user'@'localhost';

-- 禁止DROP/ALTER等危险操作
REVOKE DROP, ALTER ON mcp_db.* FROM 'mcp_user'@'localhost';
```

---

## 📈 性能优化

### 1. 索引检查

```sql
-- 查看表索引
SHOW INDEX FROM long_memories;
SHOW INDEX FROM audit_logs;

-- 检查慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = 'ON';
```

### 2. 连接池配置

```python
# 根据并发调整
pool_size = 连接数
max_overflow = 峰值额外连接

# 推荐配置:
# 开发: pool_size=5, max_overflow=5
# 测试: pool_size=10, max_overflow=10
# 生产: pool_size=20, max_overflow=20
```

### 3. Query优化

```sql
-- 分析查询
EXPLAIN SELECT * FROM long_memories WHERE project_id = 'xxx';

-- 添加索引
CREATE INDEX idx_custom ON table_name(column_name);
```

---

## 🔄 PostgreSQL迁移对比

### 主要变化

| 特性 | PostgreSQL | MySQL |
|------|------------|-------|
| 驱动 | psycopg2-binary | pymysql |
| URL前缀 | postgresql:// | mysql+pymysql:// |
| 端口 | 5432 | 3306 |
| DateTime | timezone=True | 不支持,使用DateTime |
| JSON | JSON/JSONB | JSON (5.7+) |
| 字符集 | UTF8 | utf8mb4 |

### 代码变化

**表定义**:
```python
# PostgreSQL
created_at = Column(DateTime(timezone=True), server_default=func.now())

# MySQL
created_at = Column(DateTime, server_default=func.now())
```

**字符集**:
```python
# MySQL添加表选项
__table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
```

---

## 📚 相关文档

- [MySQL官方文档](https://dev.mysql.com/doc/)
- [SQLAlchemy MySQL方言](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [PyMySQL文档](https://pymysql.readthedocs.io/)
- `QUICKSTART.md` - 快速启动指南
- `PHASE6_COMPLETION_REPORT.md` - Phase 6报告

---

**MCP项目 - MySQL数据库配置完成！** ✅
