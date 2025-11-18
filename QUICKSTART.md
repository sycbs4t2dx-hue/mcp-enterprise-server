# MCP 快速启动指南

> 5分钟快速部署MCP系统

## 📋 前置准备

确保已安装:
- Python 3.10+
- MySQL 5.7+ (已启动)
- Git

## 🚀 安装步骤

### 1. 进入项目目录

```bash
cd /Users/mac/Downloads/MCP
```

### 2. 安装Python依赖

```bash
./install_dependencies.sh
```

或手动安装:

```bash
pip3 install fastapi uvicorn sqlalchemy pymysql redis pymilvus \
    sentence-transformers torch transformers scikit-learn \
    python-jose passlib pydantic-settings pyyaml
```

### 3. 创建MySQL数据库

```bash
mysql -u root -p
```

在MySQL中执行:

```sql
CREATE DATABASE mcp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

或使用脚本:

```bash
mysql -u root -p < scripts/setup_mysql.sql
```

### 4. 配置数据库连接

编辑 `config.yaml`，确认数据库配置:

```yaml
database:
  url: "mysql+pymysql://root:你的密码@localhost:3306/mcp_db?charset=utf8mb4"
```

### 5. 初始化数据表

```bash
python3 scripts/init_database.py
```

成功后会看到:

```
✓ MySQL版本: x.x.x
✓ 数据库连接正常
✓ 数据库表创建成功
✓ 初始数据插入成功
  - 管理员账号: admin / admin123
  - 测试账号: testuser / test123
```

### 6. 启动服务

```bash
./start.sh
```

或:

```bash
python3 -m uvicorn src.mcp_core.main:app --reload --host 0.0.0.0 --port 8000
```

## ✅ 验证安装

### 1. 检查健康状态

```bash
curl http://localhost:8000/health
```

应返回:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "unhealthy: ...",
    "milvus": "not_initialized"
  }
}
```

### 2. 访问API文档

打开浏览器访问: http://localhost:8000/docs

### 3. 测试登录API

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

应返回JWT token:

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

## 🎯 下一步

### 使用API文档测试

1. 访问 http://localhost:8000/docs
2. 点击右上角 "Authorize" 按钮
3. 使用admin账号登录获取token
4. 输入token (格式: `Bearer <your_token>`)
5. 尝试各个API端点

### 基本操作流程

1. **登录** → 获取Token
2. **创建项目** → `POST /api/v1/project/create`
3. **存储记忆** → `POST /api/v1/memory/store`
4. **检索记忆** → `POST /api/v1/memory/retrieve`
5. **压缩内容** → `POST /api/v1/token/compress`
6. **检测幻觉** → `POST /api/v1/validate/detect`

## 🔧 可选组件

### Redis (缓存加速)

```bash
# macOS
brew install redis
redis-server

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis
```

更新 `config.yaml`:

```yaml
redis:
  url: "redis://localhost:6379/0"
```

### Milvus (语义检索)

使用Docker安装:

```bash
# 下载docker-compose配置
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动
docker-compose up -d
```

更新 `config.yaml`:

```yaml
vector_db:
  type: "milvus"
  milvus:
    host: "localhost"
    port: 19530
```

## ❓ 常见问题

### Q1: 数据库连接失败

**错误**: `Can't connect to MySQL server`

**解决**:
1. 确认MySQL已启动: `mysql -u root -p`
2. 检查密码是否正确
3. 确认数据库已创建: `SHOW DATABASES LIKE 'mcp_db';`

### Q2: 导入失败 ModuleNotFoundError

**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决**:

```bash
# 重新安装依赖
./install_dependencies.sh

# 或手动安装缺失的包
pip3 install <package_name>
```

### Q3: 端口被占用

**错误**: `Address already in use`

**解决**:

```bash
# 查找占用8000端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
uvicorn src.mcp_core.main:app --port 8001
```

### Q4: HuggingFace模型下载失败

**现象**: 启动时尝试下载sentence-transformers模型失败

**解决**:

方式1: 配置镜像 (临时方案)

```bash
export HF_ENDPOINT=https://hf-mirror.com
./start.sh
```

方式2: 离线模式 (开发中)

```bash
# 待实现：使用本地模型
```

## 📚 相关文档

- [README.md](README.md) - 项目概述
- [MYSQL_SETUP.md](MYSQL_SETUP.md) - MySQL详细配置
- [PHASE6_COMPLETION_REPORT.md](PHASE6_COMPLETION_REPORT.md) - API实现报告

## 🆘 获取帮助

- 查看日志: `tail -f logs/mcp.log`
- 验证配置: `python3 scripts/verify_config.py`
- 运行测试: `pytest tests/unit/ -v`
- API文档: http://localhost:8000/docs

---

**需要帮助?** 查看完整文档或运行 `./start.sh` 查看启动信息
