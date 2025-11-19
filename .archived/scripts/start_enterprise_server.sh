#!/bin/bash
# MCP Enterprise Server 启动脚本

echo "🚀 MCP Enterprise Server v2.0.0"
echo "=========================================="
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv_mcp" ]; then
    echo "📦 激活虚拟环境..."
    source venv_mcp/bin/activate
fi

# 加载环境变量
if [ -f ".env" ]; then
    echo "📋 加载环境变量..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  未找到.env文件，使用默认配置"
    export DB_PASSWORD="${DB_PASSWORD:-Wxwy.2025@#}"
fi

# 检查Docker服务
echo ""
echo "📦 检查Docker服务..."
if ! docker ps | grep -q "mcp-mysql\|mcp-redis\|mcp-milvus"; then
    echo "⚠️  Docker服务未运行，正在启动..."
    docker start mcp-mysql mcp-redis mcp-milvus
    sleep 5
fi

docker ps --filter "name=mcp-" --format "✅ {{.Names}} - {{.Status}}"
echo ""

# 获取本机IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo "🌐 网络信息:"
echo "  本机IP: $LOCAL_IP"
echo "  服务端口: ${PORT:-8765}"
echo ""

# 解析可选参数
ARGS="--host ${HOST:-0.0.0.0} --port ${PORT:-8765}"

# 添加API密钥（如果配置）
if [ -n "$API_KEYS" ]; then
    IFS=',' read -ra KEYS <<< "$API_KEYS"
    for key in "${KEYS[@]}"; do
        ARGS="$ARGS --api-key $key"
    done
    echo "🔒 API密钥认证: 已启用 (${#KEYS[@]}个密钥)"
fi

# 添加IP白名单（如果配置）
if [ -n "$ALLOWED_IPS" ]; then
    IFS=',' read -ra IPS <<< "$ALLOWED_IPS"
    for ip in "${IPS[@]}"; do
        ARGS="$ARGS --allowed-ip $ip"
    done
    echo "🛡️  IP白名单: 已启用 (${#IPS[@]}个IP)"
fi

# 添加性能参数
ARGS="$ARGS --rate-limit ${RATE_LIMIT:-100}"
ARGS="$ARGS --max-connections ${MAX_CONNECTIONS:-1000}"

echo ""
echo "📋 同事配置（复制到Claude Code）:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "mcp-remote": {'
echo "      \"url\": \"http://$LOCAL_IP:${PORT:-8765}\""
echo '    }'
echo '  }'
echo '}'
echo ""

echo "🔧 启动服务器..."
echo "  信息页面: http://$LOCAL_IP:${PORT:-8765}/info"
echo "  健康检查: http://$LOCAL_IP:${PORT:-8765}/health"
echo "  监控指标: http://$LOCAL_IP:${PORT:-8765}/metrics"
echo ""
echo "  按 Ctrl+C 停止服务器"
echo ""

# 启动企业级服务器
python3 mcp_server_enterprise.py $ARGS
