# 🚀 MCP Enterprise Server v2.0.0 - 完整部署指南

## 📋 概述

MCP Enterprise Server是生产级MCP服务器，提供：

✅ **多传输方式**: stdio, HTTP, SSE (WebSocket规划中)
✅ **企业级安全**: API密钥认证, IP白名单, CORS
✅ **性能优化**: 请求限流, 并发控制, 连接池
✅ **完整监控**: 实时统计, Prometheus指标, 结构化日志
✅ **高可用**: 健康检查, 优雅关闭, 错误恢复

---

## 🎯 三种部署模式

### 模式1: 本机开发（stdio）

**适用场景**: 个人开发，本机使用

**配置**:
```json
{
  "mcpServers": {
    "mcp-local": {
      "command": "python3",
      "args": ["/Users/mac/Downloads/MCP/mcp_server_unified.py"],
      "env": {
        "DB_PASSWORD": "Wxwy.2025@#"
      }
    }
  }
}
```

**优点**: 无网络开销, 最高性能
**缺点**: 仅本机可用

---

### 模式2: 局域网简单模式（HTTP）

**适用场景**: 小团队，信任网络环境

**启动**:
```bash
./start_sse_server.sh  # 使用简单版服务器
```

**配置**:
```json
{
  "mcpServers": {
    "mcp-remote": {
      "url": "http://192.168.3.5:8765"
    }
  }
}
```

**优点**: 配置简单, 无需认证
**缺点**: 无安全控制

---

### 模式3: 企业生产模式（推荐）

**适用场景**: 企业环境，需要安全控制和监控

**步骤1: 配置环境变量**
```bash
cp .env.example .env
vim .env
```

编辑`.env`文件:
```bash
# 基础配置
HOST=0.0.0.0
PORT=8765
DB_PASSWORD=Wxwy.2025@#

# 安全配置
API_KEYS=sk-prod-abc123,sk-prod-xyz789
ALLOWED_IPS=192.168.1.10,192.168.1.20,192.168.1.30

# 性能配置
RATE_LIMIT=100
MAX_CONNECTIONS=1000
```

**步骤2: 启动服务器**
```bash
./start_enterprise_server.sh
```

**步骤3: 同事配置**
```json
{
  "mcpServers": {
    "mcp-remote": {
      "url": "http://192.168.3.5:8765",
      "headers": {
        "Authorization": "Bearer sk-prod-abc123"
      }
    }
  }
}
```

**优点**: 完整安全控制, 监控告警, 生产就绪
**缺点**: 配置稍复杂

---

## 🛠️ 功能详解

### 1. 安全认证

#### API密钥认证
```bash
# 启动时指定API密钥
python3 mcp_server_enterprise.py \
  --api-key sk-key1 \
  --api-key sk-key2
```

客户端请求需携带Authorization头:
```
Authorization: Bearer sk-key1
```

#### IP白名单
```bash
# 只允许特定IP访问
python3 mcp_server_enterprise.py \
  --allowed-ip 192.168.1.10 \
  --allowed-ip 192.168.1.20
```

### 2. 性能控制

#### 请求限流
```bash
# 每60秒最多100个请求
--rate-limit 100
```

超过限流返回429错误:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

#### 并发控制
```bash
# 最多1000个并发连接
--max-connections 1000
```

超过限制返回503错误:
```json
{
  "error": "Server at capacity"
}
```

### 3. 监控端点

#### 健康检查 (/health)
```bash
curl http://192.168.3.5:8765/health
```

响应:
```json
{
  "status": "healthy",
  "version": "v2.0.0",
  "uptime_seconds": 3600,
  "tools_count": 37,
  "active_connections": 5,
  "total_requests": 1234,
  "timestamp": "2025-01-19T12:00:00Z"
}
```

#### 统计数据 (/stats)
```bash
curl http://192.168.3.5:8765/stats
```

响应:
```json
{
  "uptime_seconds": 3600,
  "total_requests": 1234,
  "successful_requests": 1200,
  "failed_requests": 34,
  "success_rate": 0.972,
  "avg_response_time": 0.123,
  "active_connections": 5,
  "recent_requests": [...]
}
```

#### Prometheus指标 (/metrics)
```bash
curl http://192.168.3.5:8765/metrics
```

响应:
```
# HELP mcp_uptime_seconds Server uptime in seconds
# TYPE mcp_uptime_seconds gauge
mcp_uptime_seconds 3600

# HELP mcp_requests_total Total number of requests
# TYPE mcp_requests_total counter
mcp_requests_total 1234
...
```

---

## 📊 监控集成

### 集成Prometheus

**prometheus.yml**:
```yaml
scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['192.168.1.34:8765']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 集成Grafana

1. 添加Prometheus数据源
2. 导入MCP仪表盘
3. 查看实时指标

**常用查询**:
```promql
# 请求速率
rate(mcp_requests_total[5m])

# 错误率
rate(mcp_requests_failed[5m]) / rate(mcp_requests_total[5m])

# 平均响应时间
mcp_response_time_avg
```

---

## 🔒 生产部署最佳实践

### 1. 使用systemd管理

创建 `/etc/systemd/system/mcp-server.service`:
```ini
[Unit]
Description=MCP Enterprise Server
After=network.target docker.service

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp
EnvironmentFile=/opt/mcp/.env
ExecStart=/usr/bin/python3 /opt/mcp/mcp_server_enterprise.py \
    --host 0.0.0.0 \
    --port 8765 \
    --rate-limit 100
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动:
```bash
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

### 2. 使用Nginx反向代理

**/etc/nginx/sites-available/mcp**:
```nginx
upstream mcp_backend {
    server 127.0.0.1:8765;
}

server {
    listen 80;
    server_name mcp.example.com;

    location / {
        proxy_pass http://mcp_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # 限流
        limit_req zone=mcp_limit burst=20 nodelay;
    }

    # SSL配置（生产环境推荐）
    # listen 443 ssl;
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;
}
```

### 3. 使用Docker部署

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8765

# 启动服务器
CMD ["python3", "mcp_server_enterprise.py", "--host", "0.0.0.0", "--port", "8765"]
```

构建和运行:
```bash
docker build -t mcp-server:v2.0.0 .
docker run -d \
  --name mcp-server \
  -p 8765:8765 \
  -e DB_PASSWORD=Wxwy.2025@# \
  --restart unless-stopped \
  mcp-server:v2.0.0
```

### 4. 使用Docker Compose（推荐）

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8765:8765"
    environment:
      - DB_PASSWORD=Wxwy.2025@#
      - API_KEYS=sk-key1,sk-key2
      - RATE_LIMIT=100
    depends_on:
      - mysql
      - redis
      - milvus
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=Wxwy.2025@#
      - MYSQL_DATABASE=mcp_db
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  milvus:
    image: milvusdb/milvus:v2.3.4
    volumes:
      - milvus_data:/var/lib/milvus

volumes:
  mysql_data:
  redis_data:
  milvus_data:
```

---

## 🐛 故障排查

### 问题1: 无法连接

**症状**: `fetch failed` 或 `Connection refused`

**排查步骤**:
```bash
# 1. 检查服务器运行
ps aux | grep mcp_server

# 2. 检查端口监听
lsof -i :8765

# 3. 检查防火墙
sudo ufw status
sudo ufw allow 8765

# 4. 查看日志
tail -f /var/log/mcp-server.log
```

### 问题2: 认证失败

**症状**: `401 Unauthorized`

**排查步骤**:
1. 检查API密钥是否正确
2. 检查Authorization头格式: `Bearer sk-xxx`
3. 检查IP是否在白名单

### 问题3: 限流触发

**症状**: `429 Rate limit exceeded`

**解决方案**:
```bash
# 调整限流配置
--rate-limit 200  # 增加到200请求/60秒
```

### 问题4: 服务器过载

**症状**: `503 Server at capacity`

**解决方案**:
```bash
# 增加最大连接数
--max-connections 2000

# 或使用负载均衡部署多个实例
```

---

## 📈 性能优化

### 1. 数据库连接池

```python
# 在mcp_server_unified.py中调整
engine = create_engine(
    database_url,
    pool_size=20,  # 连接池大小
    max_overflow=40,  # 溢出连接数
    pool_pre_ping=True  # 连接检查
)
```

### 2. Redis缓存优化

```python
# 启用缓存
@lru_cache(maxsize=1000)
def get_tools_list():
    return self.mcp_server.get_all_tools()
```

### 3. 异步优化

当前版本已使用asyncio，未来可进一步优化:
- 工具调用异步化
- 数据库查询批处理
- 并行处理多个请求

---

## 🔐 安全加固

### 1. 使用HTTPS

```bash
# 生成自签名证书（测试用）
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 生产环境使用Let's Encrypt
certbot certonly --standalone -d mcp.example.com
```

### 2. 密钥管理

```bash
# 使用环境变量
export MCP_API_KEYS="$(cat /secure/path/api_keys.txt)"

# 或使用Kubernetes Secrets
kubectl create secret generic mcp-secrets \
  --from-literal=api-key-1=sk-xxx \
  --from-literal=db-password=xxx
```

### 3. 审计日志

```python
# 记录所有敏感操作
logger.audit({
    "user": user_id,
    "action": "tool_call",
    "tool": tool_name,
    "ip": client_ip,
    "timestamp": datetime.now().isoformat()
})
```

---

## ✅ 快速启动检查清单

### 服务器端
- [ ] Docker服务运行中（MySQL/Redis/Milvus）
- [ ] 设置DB_PASSWORD环境变量
- [ ] 配置API密钥（如需要）
- [ ] 配置IP白名单（如需要）
- [ ] 启动MCP服务器
- [ ] 验证 /health 端点

### 客户端
- [ ] 获取服务器URL
- [ ] 获取API密钥（如需要）
- [ ] 配置Claude Code
- [ ] 重启Claude Code
- [ ] 测试工具列表

---

## 📞 技术支持

遇到问题请检查:
1. 服务器日志
2. /health 健康检查
3. /stats 统计数据
4. /metrics Prometheus指标

---

**MCP Enterprise Server v2.0.0 - 生产就绪的MCP服务器！** 🚀
