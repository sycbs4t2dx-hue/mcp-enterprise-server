#!/bin/bash
#
# MCP远程服务快速部署脚本
# 用法: ./deploy.sh
#

set -e  # 遇到错误立即退出

echo "========================================"
echo "MCP远程服务部署脚本"
echo "========================================"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    echo "运行: curl -fsSL https://get.docker.com | bash"
    exit 1
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    echo "运行: sudo apt-get install docker-compose -y"
    exit 1
fi

echo "✓ Docker环境检查通过"
echo ""

# 配置域名
read -p "请输入您的域名（如 mcp.example.com）: " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo "❌ 域名不能为空"
    exit 1
fi

# 配置MySQL密码
read -sp "请设置MySQL root密码: " MYSQL_PASSWORD
echo ""
if [ -z "$MYSQL_PASSWORD" ]; then
    echo "❌ 密码不能为空"
    exit 1
fi

# 生成.env文件
echo ""
echo "正在生成配置文件..."
cat > .env << EOF
MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD
DATABASE_URL=mysql+pymysql://root:$MYSQL_PASSWORD@mysql:3306/mcp_db?charset=utf8mb4
REDIS_URL=redis://redis:6379/0
SERVER_DOMAIN=$DOMAIN
EOF

# 更新nginx配置
echo "更新nginx配置..."
sed -i.bak "s/mcp.yourdomain.com/$DOMAIN/g" nginx/nginx.conf

# 更新config.yaml
echo "更新数据库配置..."
cat > config.yaml << EOF
app:
  name: "MCP Memory Server"
  version: "1.1.0"
  debug: false

database:
  url: "mysql+pymysql://root:$MYSQL_PASSWORD@mysql:3306/mcp_db?charset=utf8mb4"
  pool_size: 20
  max_overflow: 10

redis:
  url: "redis://redis:6379/0"
  enabled: true

security:
  jwt:
    secret_key: "$(openssl rand -base64 64 | tr -d '\n')"
    algorithm: "HS256"
    access_token_expire_minutes: 1440
EOF

echo "✓ 配置文件生成完成"
echo ""

# 启动服务
echo "正在启动服务..."
docker-compose -f docker-compose.mcp.yml down 2>/dev/null || true
docker-compose -f docker-compose.mcp.yml up -d --build

echo ""
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "检查服务状态..."
docker-compose -f docker-compose.mcp.yml ps

# 初始化数据库
echo ""
echo "初始化数据库..."
docker exec -it mcp-http-server python3 scripts/init_database.py || echo "⚠️  数据库初始化可能需要手动执行"

# 创建第一个API Key
echo ""
echo "创建初始API Key..."
FIRST_API_KEY=$(curl -s -X POST http://localhost:8001/api/keys/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","description":"Initial admin key"}' | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)

echo ""
echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "服务信息:"
echo "  - 域名: $DOMAIN"
echo "  - HTTP端口: 80"
echo "  - HTTPS端口: 443"
echo "  - MCP端点: https://$DOMAIN/mcp"
echo ""
echo "首个API Key:"
echo "  $FIRST_API_KEY"
echo ""
echo "⚠️  请保存好这个API Key，它只显示一次！"
echo ""
echo "下一步:"
echo "  1. 配置域名DNS解析到服务器IP"
echo "  2. 配置SSL证书（推荐Let's Encrypt）:"
echo "     sudo certbot --nginx -d $DOMAIN"
echo "  3. 用户配置Claude Desktop:"
echo "     编辑 claude_desktop_config.json，添加:"
echo ""
echo '     {
       "mcpServers": {
         "remote-mcp": {
           "url": "https://'$DOMAIN'/mcp",
           "transport": "http",
           "headers": {
             "Authorization": "Bearer '$FIRST_API_KEY'"
           }
         }
       }
     }'
echo ""
echo "查看日志: docker-compose -f docker-compose.mcp.yml logs -f"
echo "========================================"
