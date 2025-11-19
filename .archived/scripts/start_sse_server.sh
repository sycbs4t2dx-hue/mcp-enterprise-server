#!/bin/bash
# MCP SSE服务器启动脚本（局域网共享）

echo "🚀 启动MCP SSE服务器 (局域网版本)"
echo "=========================================="
echo ""

# 激活虚拟环境
if [ -d "venv_mcp" ]; then
    echo "📦 激活虚拟环境..."
    source venv_mcp/bin/activate
fi

# 设置数据库密码
export DB_PASSWORD="Wxwy.2025@#"

# 检查Docker服务
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
echo "  服务端口: 8765"
echo ""

echo "📋 同事只需要在Claude Code配置中添加:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "mcp-remote": {'
echo "      \"url\": \"http://$LOCAL_IP:8765/sse\""
echo '    }'
echo '  }'
echo '}'
echo ""

echo "🔧 启动服务器..."
echo "  浏览器访问: http://$LOCAL_IP:8765"
echo "  按 Ctrl+C 停止服务器"
echo ""

# 启动HTTP服务器（简化版）
python3 mcp_server_http_simple.py --host 0.0.0.0 --port 8765
