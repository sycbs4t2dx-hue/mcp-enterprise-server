# MCP系统部署与维护指南

> 版本: v3.0.0
> 更新日期: 2025-11-21
> 适用环境: Production / Staging / Development

---

## 快速开始

### 系统要求

| 组件 | 最低要求 | 推荐配置 |
|-----|---------|---------|
| CPU | 4 核 | 8 核 |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 50 GB SSD | 100 GB SSD |
| Python | 3.9+ | 3.11 |
| Node.js | 16+ | 18 LTS |
| Docker | 20.10+ | Latest |

### 30秒快速部署

```bash
# 克隆项目
git clone https://github.com/your-org/mcp-system.git
cd mcp-system

# 一键部署
./deploy.sh production

# 验证部署
curl http://localhost:8000/health
```

---

## 一、环境准备

### 1.1 基础服务安装

#### Docker服务
```bash
# 安装Docker
curl -fsSL https://get.docker.com | bash

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加当前用户到docker组
sudo usermod -aG docker $USER
```

#### Python环境
```bash
# 安装Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate
```

#### Node.js环境
```bash
# 使用nvm安装Node.js
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

### 1.2 依赖服务部署

```bash
# 启动所有依赖服务
./start_services.sh

# 或手动启动各服务
docker-compose up -d mysql redis milvus
```

验证服务状态:
```bash
# 检查服务运行状态
docker-compose ps

# 应该看到:
# mcp_mysql_1    Up    3306/tcp
# mcp_redis_1    Up    6379/tcp
# mcp_milvus_1   Up    19530/tcp
```

---

## 二、系统部署

### 2.1 配置文件设置

```bash
# 复制配置模板
cp config_unified.yaml.example config_unified.yaml

# 编辑配置文件
vim config_unified.yaml
```

关键配置项:

```yaml
# 数据库配置
database:
  url: mysql+pymysql://root:${DB_PASSWORD}@localhost:3306/mcp_db
  pool_size: 20  # 根据负载调整

# Redis配置
redis:
  host: ${REDIS_HOST:-localhost}
  port: ${REDIS_PORT:-6379}
  password: ${REDIS_PASSWORD}  # 生产环境必须设置

# API安全配置
api:
  api_keys:
    - ${API_KEY_1}
    - ${API_KEY_2}
  rate_limit: 100  # 每分钟请求限制
```

### 2.2 环境变量配置

创建 `.env` 文件:

```bash
cat > .env << EOF
# 数据库
DB_PASSWORD=your_secure_password
DATABASE_URL=mysql+pymysql://root:your_secure_password@localhost:3306/mcp_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# API安全
API_KEY_1=sk-xxxxxxxxxxxxxxxxxxxx
API_KEY_2=sk-yyyyyyyyyyyyyyyyyyyy

# 日志
LOG_LEVEL=INFO

# 配置热重载（生产环境建议关闭）
CONFIG_HOT_RELOAD=false

# 性能监控
ENABLE_PROFILING=false
ENABLE_METRICS=true
EOF
```

### 2.3 数据库初始化

```bash
# 创建数据库
mysql -u root -p << EOF
CREATE DATABASE IF NOT EXISTS mcp_db CHARACTER SET utf8mb4;
EOF

# 运行迁移脚本
python scripts/migrate_database.py

# 初始化向量数据库集合
python scripts/init_milvus.py
```

### 2.4 安装Python依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装可选依赖（性能监控）
pip install -r requirements-monitoring.txt
```

### 2.5 前端构建

```bash
# 进入前端目录
cd mcp-admin-ui

# 安装依赖
npm install

# 构建生产版本
npm run build

# 返回根目录
cd ..
```

### 2.6 启动服务

```bash
# 使用完整重启脚本
./restart_server_complete.sh

# 或分别启动各服务
python mcp_server_enterprise.py &  # HTTP API服务
python mcp_server_unified.py &     # MCP服务
python src/mcp_core/services/websocket_service.py &  # WebSocket服务
```

---

## 三、部署验证

### 3.1 健康检查

```bash
# API健康检查
curl http://localhost:8000/health

# 预期响应:
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,
    "milvus": true
  },
  "timestamp": "2025-11-21T10:00:00Z"
}
```

### 3.2 功能测试

```bash
# 运行集成测试
./run_tests.sh integration

# 运行性能基准测试
./run_tests.sh performance

# 检查WebSocket连接
wscat -c ws://localhost:8765/ws
> {"type": "ping"}
< {"type": "pong", "timestamp": ...}
```

### 3.3 前端访问

```bash
# 打开浏览器访问
open http://localhost:5175

# 或使用curl测试
curl http://localhost:5175/
```

---

## 四、生产环境部署

### 4.1 使用Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  mcp-api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    ports:
      - "8000:8000"
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./mcp-admin-ui/dist:/usr/share/nginx/html:ro
    ports:
      - "80:80"
      - "443:443"
    restart: always
```

部署命令:
```bash
docker-compose -f docker-compose.production.yml up -d
```

### 4.2 使用Kubernetes

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-api
  template:
    metadata:
      labels:
        app: mcp-api
    spec:
      containers:
      - name: mcp-api
        image: your-registry/mcp-api:v3.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
```

部署到Kubernetes:
```bash
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml
kubectl apply -f k8s-ingress.yaml
```

### 4.3 负载均衡配置

Nginx配置示例:
```nginx
upstream mcp_backend {
    least_conn;
    server 127.0.0.1:8001 weight=1;
    server 127.0.0.1:8002 weight=1;
    server 127.0.0.1:8003 weight=1;
}

server {
    listen 80;
    server_name api.mcp-system.com;

    location / {
        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 五、日常维护

### 5.1 日志管理

```bash
# 查看实时日志
tail -f logs/mcp.log

# 查看错误日志
grep ERROR logs/mcp.log

# 日志轮转配置
cat > /etc/logrotate.d/mcp << EOF
/path/to/mcp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 5.2 数据库维护

```bash
# 备份数据库
mysqldump -u root -p mcp_db > backup_$(date +%Y%m%d).sql

# 定期优化表
mysql -u root -p mcp_db -e "OPTIMIZE TABLE long_term_memories;"

# 清理过期数据
python scripts/cleanup_old_data.py --days=30
```

### 5.3 缓存管理

```python
# 清理缓存
from src.mcp_core.services.cache_integration import get_cache_integration

cache = get_cache_integration()
cache.clear_all()  # 清理所有缓存
cache.clear_l1()   # 只清理L1缓存
```

### 5.4 性能监控

```bash
# 运行性能测试
./run_tests.sh performance

# 生成性能报告
python scripts/generate_performance_report.py

# 监控系统资源
htop
docker stats
```

---

## 六、故障排查

### 6.1 常见问题

#### 问题1: WebSocket连接失败
```bash
# 检查端口占用
lsof -i :8765

# 重启WebSocket服务
pkill -f websocket_service.py
python src/mcp_core/services/websocket_service.py &

# 检查防火墙
sudo ufw allow 8765
```

#### 问题2: 数据库连接池耗尽
```python
# 增加连接池大小
from src.mcp_core.services.unified_config import config_set
config_set("database.pool_size", 50)

# 或修改配置文件
database:
  pool_size: 50
  max_overflow: 20
```

#### 问题3: Redis连接超时
```bash
# 检查Redis状态
redis-cli ping

# 增加超时时间
export REDIS_TIMEOUT=10

# 清理Redis内存
redis-cli FLUSHDB
```

#### 问题4: 向量检索缓慢
```python
# 重建Milvus索引
from src.mcp_core.services.vector_db import get_vector_db

vector_db = get_vector_db()
vector_db.rebuild_index("mid_term_memories")
```

### 6.2 调试工具

```bash
# 启用调试模式
export DEBUG=true
export LOG_LEVEL=DEBUG

# 使用性能分析
python -m cProfile -o profile.stats mcp_server_enterprise.py

# 分析结果
python -m pstats profile.stats
```

### 6.3 紧急回滚

```bash
# 回滚到上一个版本
git checkout v2.0.0
./deploy.sh rollback

# 从备份恢复数据库
mysql -u root -p mcp_db < backup_20251120.sql
```

---

## 七、性能优化

### 7.1 系统调优

```bash
# 调整系统参数
sudo sysctl -w net.core.somaxconn=1024
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=2048

# 持久化配置
echo "net.core.somaxconn=1024" >> /etc/sysctl.conf
```

### 7.2 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_created_at ON long_term_memories(created_at);
CREATE INDEX idx_user_project ON project_sessions(user_id, project_id);

-- 分区表（大数据量）
ALTER TABLE long_term_memories PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026)
);
```

### 7.3 缓存策略

```python
# 预热缓存
def warm_up_cache():
    frequently_used_queries = load_frequent_queries()
    for query in frequently_used_queries:
        cache.set(query.key, query.result, ttl=3600)

# 定时执行
schedule.every().hour.do(warm_up_cache)
```

---

## 八、监控告警

### 8.1 Prometheus集成

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-api'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
```

### 8.2 告警规则

```yaml
# alert-rules.yml
groups:
- name: mcp_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate detected"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes > 1e9
    for: 10m
    annotations:
      summary: "Memory usage exceeds 1GB"
```

### 8.3 通知配置

```python
# 邮件告警
def send_alert(message):
    smtp_client.send_email(
        to=["ops@company.com"],
        subject="MCP System Alert",
        body=message
    )

# Slack通知
def send_slack_notification(message):
    slack_webhook.post(json={"text": message})
```

---

## 九、安全加固

### 9.1 API安全

```python
# API密钥轮换
def rotate_api_keys():
    new_keys = generate_new_keys()
    update_config({"api.api_keys": new_keys})
    notify_key_holders(new_keys)
```

### 9.2 数据加密

```bash
# 启用TLS
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# 配置HTTPS
api:
  ssl_cert: /path/to/cert.pem
  ssl_key: /path/to/key.pem
```

### 9.3 访问控制

```python
# IP白名单
ALLOWED_IPS = ["10.0.0.0/8", "192.168.0.0/16"]

@app.middleware("http")
async def ip_whitelist(request, call_next):
    client_ip = request.client.host
    if not is_ip_allowed(client_ip, ALLOWED_IPS):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    return await call_next(request)
```

---

## 十、灾难恢复

### 10.1 备份策略

```bash
# 自动备份脚本
#!/bin/bash
BACKUP_DIR="/backups/mcp"
DATE=$(date +%Y%m%d_%H%M%S)

# 数据库备份
mysqldump -u root -p$DB_PASSWORD mcp_db > $BACKUP_DIR/db_$DATE.sql

# 配置文件备份
tar -czf $BACKUP_DIR/config_$DATE.tar.gz *.yaml .env

# 向量数据备份
python scripts/backup_milvus.py --output=$BACKUP_DIR/vectors_$DATE.bin

# 保留30天
find $BACKUP_DIR -type f -mtime +30 -delete
```

### 10.2 恢复流程

```bash
# 1. 停止服务
./stop_all_services.sh

# 2. 恢复数据
mysql -u root -p mcp_db < backup.sql
tar -xzf config_backup.tar.gz
python scripts/restore_milvus.py --input=vectors_backup.bin

# 3. 重启服务
./restart_server_complete.sh

# 4. 验证恢复
./run_tests.sh integration
```

---

## 十一、版本升级

### 11.1 升级检查清单

- [ ] 备份所有数据
- [ ] 检查依赖兼容性
- [ ] 测试环境验证
- [ ] 准备回滚方案
- [ ] 通知相关人员
- [ ] 监控资源使用

### 11.2 升级步骤

```bash
# 1. 拉取新版本
git fetch origin
git checkout v3.1.0

# 2. 更新依赖
pip install -r requirements.txt --upgrade
npm install

# 3. 运行迁移
python scripts/migrate_database.py

# 4. 重新构建
npm run build
docker build -t mcp-api:v3.1.0 .

# 5. 滚动更新
kubectl set image deployment/mcp-api mcp-api=mcp-api:v3.1.0

# 6. 验证
./run_tests.sh all
```

---

## 十二、团队协作

### 12.1 开发环境搭建

```bash
# 开发环境快速搭建
git clone https://github.com/your-org/mcp-system.git
cd mcp-system
./setup_dev_env.sh

# 创建feature分支
git checkout -b feature/your-feature
```

### 12.2 代码规范

```bash
# 运行代码检查
black src/ --check
flake8 src/
mypy src/

# 运行测试
pytest tests/ --cov=src
```

### 12.3 部署流程

```mermaid
graph LR
    A[开发] --> B[测试]
    B --> C[预发布]
    C --> D[生产]
    D --> E[监控]
    E --> F[优化]
    F --> A
```

---

## 支持与资源

### 官方文档
- [API文档](http://localhost:8000/docs)
- [系统架构](./docs/ARCHITECTURE.md)
- [性能调优](./docs/PERFORMANCE.md)

### 社区支持
- GitHub Issues: https://github.com/your-org/mcp-system/issues
- Discord: https://discord.gg/mcp-system
- Stack Overflow: [mcp-system] tag

### 紧急联系
- 运维值班: ops@company.com
- 24/7热线: +1-xxx-xxx-xxxx

---

**文档版本**: v1.0
**最后更新**: 2025-11-21
**维护团队**: MCP Operations Team