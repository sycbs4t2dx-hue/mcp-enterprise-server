# ⚠️ MCP 端口冲突分析与解决方案

**发现时间**: 2025-01-19
**问题类型**: 端口冲突
**影响范围**: MySQL, Redis

---

## 🔍 问题分析

### 当前端口占用情况

```
端口 6379 (Redis):
  - 本地Redis (PID: 16984) ← 本机安装
  - Docker Redis (PID: 25172) ← 容器
  ❌ 冲突！

端口 3306 (MySQL):
  - 本地MySQL (PID: 51803) ← 本机安装
  - Docker MySQL (PID: 25172) ← 容器
  ❌ 冲突！

端口 19530 (Milvus):
  - Docker Milvus (PID: 25172) ← 仅容器
  ✅ 无冲突
```

### 冲突后果

1. **服务混乱**: MCP服务器可能连接到错误的数据库
2. **数据不一致**: 本地和Docker数据库数据不同步
3. **配置复杂**: 需要明确指定连接目标

---

## 💡 解决方案对比

### 方案1: 停止本地服务 (推荐 ⭐⭐⭐⭐⭐)

**优点**:
- ✅ 环境隔离，Docker统一管理
- ✅ 数据一致性好
- ✅ 易于备份和迁移
- ✅ 端口使用标准

**缺点**:
- ⚠️ 需要停止本地已有的MySQL/Redis

**适用场景**:
- MCP是主要使用的系统
- 希望环境隔离
- 便于团队协作

**执行步骤**:
```bash
# 1. 停止本地服务
brew services stop mysql
brew services stop redis

# 或直接kill进程
pkill -f mysqld
pkill -f redis-server

# 2. 确认Docker容器运行
docker ps | grep mcp

# 3. 启动MCP服务器
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_unified.py
```

---

### 方案2: 停止Docker容器 (替代方案 ⭐⭐⭐)

**优点**:
- ✅ 保持现有本地服务不变
- ✅ 无需学习Docker
- ✅ 本地服务性能可能更好

**缺点**:
- ❌ 需要手动创建数据库和表
- ❌ 数据和本地其他应用混在一起
- ❌ 备份和迁移较麻烦
- ❌ Milvus仍需Docker

**适用场景**:
- 本地MySQL/Redis有其他重要应用
- 不想改变现有环境

**执行步骤**:
```bash
# 1. 停止Docker容器
docker stop mcp-mysql mcp-redis

# 2. 连接本地MySQL创建数据库
mysql -uroot -p
CREATE DATABASE mcp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

# 3. 修改配置文件
vim config/mcp_config.json
# 修改password为本地MySQL密码

# 4. 创建数据表
export DB_PASSWORD="你的本地MySQL密码"
python3 setup.py --create-tables

# 5. 启动MCP服务器
python3 mcp_server_unified.py
```

---

### 方案3: 修改Docker端口 (共存方案 ⭐⭐⭐⭐)

**优点**:
- ✅ 本地和Docker服务可以共存
- ✅ 不影响现有应用
- ✅ 灵活性最高

**缺点**:
- ⚠️ 端口号非标准
- ⚠️ 配置文件需要修改多处
- ⚠️ 容易混淆

**适用场景**:
- 需要同时使用本地和Docker服务
- 开发测试环境

**新端口映射**:
```
MySQL:  localhost:3307 (Docker) vs :3306 (本地)
Redis:  localhost:6380 (Docker) vs :6379 (本地)
Milvus: localhost:19530 (Docker) - 无冲突
```

**执行步骤**:
```bash
# 1. 运行自动脚本
./fix_port_conflicts.sh
# 选择选项 3

# 2. 修改配置文件
vim config/mcp_config.json

# 修改为:
{
  "database": {
    "host": "localhost",
    "port": 3307,  // ← 改为3307
    "user": "root",
    "password": "Wxwy.2025@#",
    "database": "mcp_db"
  }
}

# 3. 修改Redis配置
# src/mcp_core/services/redis_client.py
# 修改端口为6380

# 4. 启动服务器
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_unified.py
```

---

## 🎯 推荐选择

### 对于您的情况，我推荐 **方案1**

**理由**:
1. MCP是完整的独立系统，应该有独立的数据环境
2. Docker容器已经创建且数据库已初始化（18张表）
3. 避免与本地其他应用的数据混淆
4. 便于未来迁移和部署

### 如何执行方案1

```bash
# 1. 运行自动脚本
./fix_port_conflicts.sh
# 选择选项 1

# 脚本会自动:
# - 停止本地MySQL
# - 停止本地Redis
# - 确保Docker容器可以使用这些端口

# 2. 启动MCP服务器
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_unified.py

# 3. 如果以后需要本地MySQL/Redis
brew services start mysql
brew services start redis
# 但需要在使用MCP前停止它们
```

---

## 📝 快速决策指南

**如果您想立即开始使用MCP**:
```bash
# 快速解决（方案1）
brew services stop mysql
brew services stop redis
export DB_PASSWORD="Wxwy.2025@#"
python3 mcp_server_unified.py
```

**如果您的本地MySQL有重要数据**:
- 使用方案3（修改Docker端口）
- 或者使用方案2（使用本地服务）

---

## ⚡ 自动化脚本

我已经创建了自动化解决脚本：

```bash
./fix_port_conflicts.sh
```

脚本会：
1. 检测当前端口占用
2. 提供3种解决方案选择
3. 自动执行相应操作
4. 给出下一步指引

---

## 🔄 快速恢复

如果选择了方案1后想恢复本地服务：

```bash
# 停止Docker
docker stop mcp-mysql mcp-redis

# 启动本地服务
brew services start mysql
brew services start redis
```

---

## ✅ 验证解决

执行方案后，验证端口：

```bash
# 检查端口占用
lsof -i :3306 -i :6379 -i :19530 | grep LISTEN

# 应该只看到一个服务占用每个端口
```

---

**建议**: 立即运行 `./fix_port_conflicts.sh` 并选择方案1，这样您可以马上开始使用MCP v2.0.0！
