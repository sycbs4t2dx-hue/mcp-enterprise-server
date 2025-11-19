# MCP远程服务器部署指南

> 将MCP服务部署到远程服务器，供所有人在Claude Code/Desktop中使用

## 🎯 部署目标

部署后可实现：
- ✅ 远程访问MCP服务（通过HTTPS）
- ✅ 多用户支持（API Key认证）
- ✅ Claude Code/Desktop集成
- ✅ 生产级可靠性（Docker + Nginx）

---

## 📋 前置要求

### 服务器要求

- **系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **CPU**: 2核+
- **内存**: 4GB+
- **硬盘**: 20GB+
- **网络**: 公网IP + 域名（推荐）

### 软件要求

```bash
# 安装Docker
curl -fsSL https://get.docker.com | bash

# 安装Docker Compose
sudo apt-get install docker-compose -y

# 验证安装
docker --version
docker-compose --version
```

---

## 🚀 快速部署

### 步骤1: 上传项目到服务器

```bash
# 本地打包
cd /Users/mac/Downloads/MCP
tar -czf mcp-server.tar.gz \
  src/ \
  scripts/ \
  config.yaml \
  docker-compose.mcp.yml \
  Dockerfile.mcp \
  requirements.txt \
  nginx/

# 上传到服务器
scp mcp-server.tar.gz user@your-server:/home/user/

# 服务器解压
ssh user@your-server
cd /home/user
tar -xzf mcp-server.tar.gz
cd mcp-server
```

### 步骤2: 配置环境变量

创建 `.env` 文件：

```bash
cat > .env << 'EOF'
# MySQL配置
MYSQL_ROOT_PASSWORD=Your-Strong-Password-Here

# 数据库URL
DATABASE_URL=mysql+pymysql://root:Your-Strong-Password-Here@mysql:3306/mcp_db?charset=utf8mb4

# Redis URL
REDIS_URL=redis://redis:6379/0

# 服务器域名（修改为您的域名）
SERVER_DOMAIN=mcp.yourdomain.com
EOF
```

### 步骤3: 更新配置

**修改 `nginx/nginx.conf`**：

```bash
# 将 mcp.yourdomain.com 替换为您的实际域名
sed -i 's/mcp.yourdomain.com/your-actual-domain.com/g' nginx/nginx.conf
```

**修改 `config.yaml`**：

```yaml
database:
  url: "mysql+pymysql://root:Your-Password@mysql:3306/mcp_db?charset=utf8mb4"

redis:
  url: "redis://redis:6379/0"
```

### 步骤4: 启动服务

```bash
# 构建并启动所有服务
docker-compose -f docker-compose.mcp.yml up -d

# 查看日志
docker-compose -f docker-compose.mcp.yml logs -f

# 检查服务状态
docker-compose -f docker-compose.mcp.yml ps
```

### 步骤5: 初始化数据库

```bash
# 进入MCP容器
docker exec -it mcp-http-server bash

# 运行初始化脚本
python3 scripts/init_database.py

# 退出容器
exit
```

### 步骤6: 配置SSL证书（HTTPS）

#### 方式A: 使用Let's Encrypt（推荐）

```bash
# 安装certbot
sudo apt-get install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d mcp.yourdomain.com

# 证书会自动配置到nginx
# 自动续期
sudo certbot renew --dry-run
```

#### 方式B: 手动配置证书

```bash
# 将证书放到nginx/ssl目录
mkdir -p nginx/ssl
cp your-cert/fullchain.pem nginx/ssl/
cp your-cert/privkey.pem nginx/ssl/

# 重启nginx
docker-compose -f docker-compose.mcp.yml restart nginx
```

### 步骤7: 创建API Key

```bash
# 访问API Key创建端点
curl -X POST https://mcp.yourdomain.com/api/keys/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user001",
    "description": "Test API Key"
  }'

# 响应示例
{
  "api_key": "mcp_xxxxxxxxxxxxx",
  "user_id": "user001",
  "description": "Test API Key",
  "created_at": "2025-01-19T..."
}
```

**保存好API Key！** 它只显示一次。

---

## 🔧 Claude Code配置

### 配置文件位置

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 配置内容

```json
{
  "mcpServers": {
    "remote-mcp-memory": {
      "url": "https://mcp.yourdomain.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer mcp_your_api_key_here"
      }
    }
  }
}
```

**重要**:
1. 将 `mcp.yourdomain.com` 替换为您的实际域名
2. 将 `mcp_your_api_key_here` 替换为步骤7获取的API Key
3. 确保使用 `https://` （如果配置了SSL）

### 验证连接

重启Claude Desktop后，您会看到：
- ✅ 工具图标（表示MCP连接成功）
- ✅ 可以使用4个工具（store_memory, retrieve_memory等）

---

## 📊 服务管理

### 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.mcp.yml ps

# 查看日志
docker-compose -f docker-compose.mcp.yml logs -f mcp-server

# 重启服务
docker-compose -f docker-compose.mcp.yml restart

# 停止服务
docker-compose -f docker-compose.mcp.yml down

# 完全重建
docker-compose -f docker-compose.mcp.yml up -d --build

# 查看资源使用
docker stats
```

### 健康检查

```bash
# 检查MCP服务
curl https://mcp.yourdomain.com/health

# 预期响应
{
  "status": "healthy",
  "service": "mcp-http-server",
  "version": "1.1.0",
  "timestamp": "2025-01-19T..."
}
```

### 备份数据

```bash
# 备份MySQL数据
docker exec mcp-mysql mysqldump -u root -p mcp_db > backup.sql

# 备份整个数据卷
docker run --rm \
  -v mcp_mysql_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mysql-backup.tar.gz /data
```

---

## 🔐 安全配置

### 1. API Key管理

**最佳实践**:
- 为每个用户创建独立API Key
- 定期轮换API Key
- 撤销不再使用的Key

```bash
# 创建新Key
curl -X POST https://mcp.yourdomain.com/api/keys/create \
  -d '{"user_id": "alice", "description": "Alice's key"}'

# 撤销Key
curl -X DELETE https://mcp.yourdomain.com/api/keys/revoke \
  -H "Authorization: Bearer mcp_xxx" \
  -d '{"api_key": "mcp_old_key"}'
```

### 2. 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 限制MySQL和Redis只能内网访问（Docker网络已隔离）
```

### 3. Nginx限流

已在 `nginx.conf` 中配置：
- 每个IP每秒最多10个请求
- 突发20个请求

调整配置：
```nginx
limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;
```

### 4. HTTPS强制

确保所有HTTP请求重定向到HTTPS（已配置）。

---

## 📈 监控与日志

### 查看日志

```bash
# MCP服务日志
docker logs -f mcp-http-server

# Nginx访问日志
docker exec mcp-nginx tail -f /var/log/nginx/mcp_access.log

# Nginx错误日志
docker exec mcp-nginx tail -f /var/log/nginx/mcp_error.log

# MySQL日志
docker logs -f mcp-mysql
```

### 日志持久化

日志已映射到宿主机：
- MCP日志: `./logs/`
- Nginx日志: `./nginx/logs/`

### 监控指标

```bash
# 资源使用
docker stats mcp-http-server

# 容器健康状态
docker inspect mcp-http-server | grep -A 10 Health
```

---

## 🐛 故障排查

### 问题1: 无法访问服务

**检查**:
```bash
# 检查容器是否运行
docker ps | grep mcp

# 检查端口监听
netstat -tlnp | grep 8001

# 检查防火墙
sudo ufw status
```

### 问题2: SSL证书错误

**解决**:
```bash
# 检查证书文件
ls -l nginx/ssl/

# 测试nginx配置
docker exec mcp-nginx nginx -t

# 重新申请证书
sudo certbot --nginx -d mcp.yourdomain.com --force-renewal
```

### 问题3: 数据库连接失败

**检查**:
```bash
# 进入MySQL容器
docker exec -it mcp-mysql mysql -u root -p

# 查看数据库
SHOW DATABASES;
USE mcp_db;
SHOW TABLES;

# 检查连接字符串
grep DATABASE_URL .env
```

### 问题4: API Key无效

**解决**:
```bash
# 进入MCP容器
docker exec -it mcp-http-server python3

# 测试创建Key
>>> from src.mcp_core.mcp_http_server import auth_manager
>>> key = auth_manager.create_api_key("test", "Test key")
>>> print(key)
```

---

## 🚀 性能优化

### 1. 增加worker数量

修改 `docker-compose.mcp.yml`:

```yaml
mcp-server:
  command: >
    uvicorn src.mcp_core.mcp_http_server:app
    --host 0.0.0.0
    --port 8001
    --workers 4  # 增加worker
```

### 2. 启用Redis缓存

确保配置文件启用Redis：

```yaml
redis:
  url: "redis://redis:6379/0"
  enabled: true
```

### 3. 数据库连接池

调整 `config.yaml`:

```yaml
database:
  pool_size: 50      # 增加连接池
  max_overflow: 20
```

---

## 💰 成本估算

### 云服务器方案

| 提供商 | 配置 | 月费用 | 适合用户数 |
|--------|------|--------|------------|
| **阿里云** | 2核4G | ~¥100 | 10-50 |
| **腾讯云** | 2核4G | ~¥100 | 10-50 |
| **AWS** | t3.medium | ~$30 | 10-50 |
| **DigitalOcean** | Basic Droplet | ~$12 | 10-30 |

### 域名 + SSL

- **域名**: ~¥50/年（.com）
- **SSL证书**: 免费（Let's Encrypt）

---

## 📚 用户使用指南

将以下内容分享给用户：

```markdown
# 使用MCP记忆服务

1. 获取API Key（联系管理员）

2. 配置Claude Desktop

编辑配置文件，添加：
{
  "mcpServers": {
    "remote-mcp": {
      "url": "https://mcp.yourdomain.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer <你的API-Key>"
      }
    }
  }
}

3. 重启Claude Desktop

4. 开始使用
   - "帮我记住项目使用FastAPI"
   - "查询之前关于数据库的信息"
   - "压缩这段长文本"
```

---

## 🎓 高级配置

### 多区域部署

使用Docker Swarm或Kubernetes进行多区域部署。

### 负载均衡

在nginx前加入云负载均衡器（如AWS ELB）。

### 数据备份自动化

```bash
# 添加crontab任务
0 2 * * * docker exec mcp-mysql mysqldump -u root -p mcp_db > /backup/mcp_$(date +\%Y\%m\%d).sql
```

---

## ✅ 部署检查清单

- [ ] 服务器准备（Docker已安装）
- [ ] 域名解析配置
- [ ] 环境变量设置
- [ ] 服务启动成功
- [ ] 数据库初始化
- [ ] SSL证书配置
- [ ] API Key创建
- [ ] 健康检查通过
- [ ] 防火墙配置
- [ ] 用户测试通过

---

**部署完成后，所有人都可以通过Claude Code/Desktop连接您的MCP服务，实现云端记忆持久化！** 🎉

---

**问题？** 查看故障排查章节或提issue。
