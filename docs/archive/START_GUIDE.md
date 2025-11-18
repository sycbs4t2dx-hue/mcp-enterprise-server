# 🚀 MCP项目启动指南

## 快速启动

### 方式1: 使用启动脚本 (推荐)

```bash
cd /Users/mac/Downloads/MCP
./start.sh
```

### 方式2: 手动启动

```bash
# 1. 进入项目目录
cd /Users/mac/Downloads/MCP

# 2. 启动服务
python3 -m uvicorn src.mcp_core.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式3: 使用uvicorn命令

```bash
cd /Users/mac/Downloads/MCP
uvicorn src.mcp_core.main:app --reload --host 0.0.0.0 --port 8000
```

## ⚠️ 重要提示

**必须在项目目录下运行启动命令！**

错误示例 ❌:
```bash
# 在其他目录运行会报错 ModuleNotFoundError: No module named 'src'
mac@HT ~ % uvicorn src.mcp_core.main:app --reload
```

正确示例 ✅:
```bash
# 必须先进入项目目录
cd /Users/mac/Downloads/MCP
uvicorn src.mcp_core.main:app --reload
```

## 🌐 访问地址

启动成功后，访问以下地址:

- **API文档 (Swagger)**: http://localhost:8000/docs
- **API文档 (ReDoc)**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

## 📝 启动日志示例

成功启动后你会看到:

```
INFO:     Will watch for changes in these directories: ['/Users/mac/Downloads/MCP']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 🛑 停止服务

按 `Ctrl + C` 停止服务

## 🔍 常见问题

### Q1: ModuleNotFoundError: No module named 'src'

**原因**: 不在项目目录下运行

**解决**:
```bash
cd /Users/mac/Downloads/MCP
./start.sh
```

### Q2: 端口已被占用

**错误**: `OSError: [Errno 48] Address already in use`

**解决**:
```bash
# 查找占用8000端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用其他端口
uvicorn src.mcp_core.main:app --reload --port 8001
```

### Q3: uvicorn: command not found

**解决**:
```bash
# 安装依赖
pip3 install -e ".[dev]"

# 或使用Python模块方式
python3 -m uvicorn src.mcp_core.main:app --reload
```

## 👥 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| testuser | test123 | 普通用户 |

## 📚 下一步

1. 访问 API 文档: http://localhost:8000/docs
2. 使用 admin 账号登录
3. 尝试创建项目、存储记忆等功能

---

**更多信息**: 查看 INIT_SUCCESS.md
